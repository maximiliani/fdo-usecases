# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""LIS file parser for BAM creep-reference usecase."""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class LISFileCollection:
    """Files belonging to one creep test."""
    test_id: str
    md_tr_checksum: str  # Vh5205_C-XX-MD-TR.lis
    creep_checksum: str  # Vh5205_C-XX-Creep.LIS
    loading_checksum: str  # Vh5205_C-XX-Loading.LIS


@dataclass
class ComplementaryFiles:
    """Shared files across all tests."""
    heat_treatment: str  # Vh5205_Complementary_Heat-treatment.LIS
    chemical_composition_measured: str  # Vh5205_Complementary_Ch.-Comp.-measured.LIS
    chemical_composition_nominal: str  # Vh5205_Complementary_Ch.-Comp.-nominal.LIS
    data_acquisition: str  # Vh5205_Complementary_Data-acquisition.LIS
    data_acquisition_creep: str  # Vh5205_Complementary_Data-acquisition-creep.LIS
    primary_processed_data: str  # Vh5205_Complementary_Primary-and-processed-data-series.LIS
    roughness: str  # Vh5205_Complementary_Roughness.LIS
    rp02: str  # Vh5205_Complementary_Rp0.2.LIS
    md_tr_common: str = ""  # Vh5205_MD-TR_Common-to-all.LIS


@dataclass
class CommonMetadata:
    """Metadata common to all tests from MD-TR_Common-to-all.LIS."""
    material_id: str = ""
    applicable_standard: str = ""
    form_of_as_manufactured_material: Optional[str] = None
    geometry_size_as_manufactured: Optional[str] = None
    geometry_size_as_tested: Optional[str] = None


@dataclass
class ParsedTestMetadata:
    """Extracted from MD-TR.lis file."""
    test_id: str
    project: str
    date_test_start: datetime
    date_test_end: datetime
    applicable_standard: str
    specified_temperature: float
    initial_stress: float
    material_id: str
    single_crystal_orientation: float
    percentage_creep_extension: float = 0.0
    manufacturing_as_manufactured: Optional[str] = None
    manufacturing_as_tested: Optional[str] = None
    file_references: list[str] = field(default_factory=list)


@dataclass
class ParsingError:
    """Represents a parsing error."""
    test_id: str
    filename: str
    error_type: str
    message: str


class LISParser:
    """Parse LIS files and extract creep test metadata.
    
    The parser works in two phases:
    1. Load file information from Zenodo FDO graph (checksums, URLs)
    2. Fetch and parse LIS file content via HTTP
    
    Attributes:
        _file_pattern: Regex for test-specific LIS files
        _complementary_pattern: Regex for complementary LIS files
        _errors: List of parsing errors encountered
        _file_collections: Grouped test files by test ID
        _complementary_files: Shared complementary files
        _file_urls: Mapping of checksums to download URLs
        _session: aiohttp session for fetching files
    """
    
    def __init__(self):
        # Flexible pattern for test-specific LIS files handling multiple naming conventions:
        # Pattern 1: Vh5205_C-XX-Type.LIS (e.g., Vh5205_C-78-MD-TR.lis, Vh5205_C-78-Creep.LIS)
        # Pattern 2: Vh5205_Type_C-XX.LIS (e.g., Vh5205_MD-TR_C-78.LIS)
        # Matches C-XX and file type anywhere in the filename
        self._test_id_pattern = re.compile(r'C-(\d+)', re.IGNORECASE)
        self._file_type_pattern = re.compile(r'(MD-TR|Creep|Loading)', re.IGNORECASE)
        self._complementary_pattern = re.compile(r'Vh\d+_Complementary_(.+)\.lis', re.IGNORECASE)
        self._md_tr_common_pattern = re.compile(r'Vh\d+_MD-TR_Common-to-all\.lis', re.IGNORECASE)
        self._errors: list[ParsingError] = []
        self._file_collections: dict[str, LISFileCollection] = {}
        self._complementary_files: Optional[ComplementaryFiles] = None
        self._common_metadata: Optional[CommonMetadata] = None
        self._file_urls: dict[str, str] = {}  # checksum -> download URL
        self._md_tr_common_checksum: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self._session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()
        
    def load_from_zenodo_graph(self, zenodo_graph: dict) -> None:
        """Extract file checksums and URLs from existing Zenodo FDO graph.
        
        Args:
            zenodo_graph: Pre-populated graph from ZenodoFDODesign
        """
        logger.info("Loading file information from Zenodo graph")
        
        # Group files by test ID
        test_files: dict[str, dict[str, str]] = {}
        complementary: dict[str, str] = {}
        
        for record_id, record in zenodo_graph.items():
            # Convert PidRecord to dict
            record_dict = record.toSimpleJSON()
            
            # Extract filename from name attribute
            name_attrs = [attr['value'] for attr in record_dict['record'] 
                         if attr['key'] == '21.T11969/bd3e9fb9b606d2198c9e']
            if not name_attrs:
                continue
                
            filename = name_attrs[0]
            
            # Skip non-LIS files (JSON translations, etc.)
            if not filename.lower().endswith('.lis'):
                continue
                
            # Extract download URL from dataObjectLocation attribute
            url_attrs = [attr['value'] for attr in record_dict['record']
                        if attr['key'] == '21.T11969/479febb2bbe8400da547']
            download_url = url_attrs[0] if url_attrs else None
            
            # Check if it's a test-specific LIS file using flexible pattern matching
            test_id_match = self._test_id_pattern.search(filename)
            file_type_match = self._file_type_pattern.search(filename)
            
            if test_id_match and file_type_match:
                # Extract test ID and file type independently of filename order
                test_id = f"Vh5205_C-{test_id_match.group(1)}"
                file_type = file_type_match.group(1).lower().replace('-', '_')
                
                if test_id not in test_files:
                    test_files[test_id] = {}
                
                # Prefer Pattern B (Vh5205_Type_C-XX.LIS) over Pattern A (Vh5205_C-XX-Type.LIS)
                # Pattern B has format: ...Type_C-XX... while Pattern A has ...C-XX-Type...
                # Check if Type comes before C-XX in filename
                type_pos = file_type_match.start()
                test_id_pos = test_id_match.start()
                is_pattern_b = type_pos < test_id_pos  # Type appears before test ID
                
                if file_type == 'md_tr':
                    # Only overwrite if this is Pattern B or if no file exists yet
                    if 'md_tr' not in test_files[test_id] or is_pattern_b:
                        test_files[test_id]['md_tr'] = record_id
                        if download_url:
                            self._file_urls[record_id] = download_url
                elif file_type == 'creep':
                    if 'creep' not in test_files[test_id] or is_pattern_b:
                        test_files[test_id]['creep'] = record_id
                        if download_url:
                            self._file_urls[record_id] = download_url
                elif file_type == 'loading':
                    if 'loading' not in test_files[test_id] or is_pattern_b:
                        test_files[test_id]['loading'] = record_id
                        if download_url:
                            self._file_urls[record_id] = download_url
                    
            # Check if it's a complementary file
            comp_match = self._complementary_pattern.match(filename)
            if comp_match:
                comp_type = comp_match.group(1).lower()
                if 'heat-treatment' in comp_type or 'heat_treatment' in comp_type:
                    complementary['heat_treatment'] = record_id
                    if download_url:
                        self._file_urls[record_id] = download_url
                elif 'ch.-comp.-measured' in comp_type or 'chemical' in comp_type:
                    complementary['chemical_measured'] = record_id
                    if download_url:
                        self._file_urls[record_id] = download_url
                elif 'ch.-comp.-nominal' in comp_type:
                    complementary['chemical_nominal'] = record_id
                    if download_url:
                        self._file_urls[record_id] = download_url
                elif 'data-acquisition-creep' in comp_type:
                    complementary['data_acquisition_creep'] = record_id
                    if download_url:
                        self._file_urls[record_id] = download_url
                elif 'data-acquisition' in comp_type:
                    complementary['data_acquisition'] = record_id
                    if download_url:
                        self._file_urls[record_id] = download_url
                elif 'primary' in comp_type:
                    complementary['primary_processed'] = record_id
                    if download_url:
                        self._file_urls[record_id] = download_url
                elif 'roughness' in comp_type:
                    complementary['roughness'] = record_id
                    if download_url:
                        self._file_urls[record_id] = download_url
                elif 'rp0.2' in comp_type or 'rp02' in comp_type:
                    complementary['rp02'] = record_id
                    if download_url:
                        self._file_urls[record_id] = download_url
            
            # Check if it's MD-TR_Common-to-all.LIS
            if self._md_tr_common_pattern.match(filename):
                self._md_tr_common_checksum = record_id
                if download_url:
                    self._file_urls[record_id] = download_url
                    logger.debug(f"Found MD-TR_Common-to-all.LIS: {record_id}")
        
        # Create file collections (only for complete sets)
        for test_id, files in test_files.items():
            if all(k in files for k in ['md_tr', 'creep', 'loading']):
                self._file_collections[test_id] = LISFileCollection(
                    test_id=test_id,
                    md_tr_checksum=files['md_tr'],
                    creep_checksum=files['creep'],
                    loading_checksum=files['loading'],
                )
            else:
                logger.warning(f"Incomplete file set for {test_id}, skipping")
                self._errors.append(ParsingError(
                    test_id=test_id,
                    filename="multiple",
                    error_type="INCOMPLETE_FILES",
                    message=f"Missing files: {set(['md_tr', 'creep', 'loading']) - set(files.keys())}"
                ))
        
        # Create complementary files object
        if complementary:
            self._complementary_files = ComplementaryFiles(
                heat_treatment=complementary.get('heat_treatment', ''),
                chemical_composition_measured=complementary.get('chemical_measured', ''),
                chemical_composition_nominal=complementary.get('chemical_nominal', ''),
                data_acquisition=complementary.get('data_acquisition', ''),
                data_acquisition_creep=complementary.get('data_acquisition_creep', ''),
                primary_processed_data=complementary.get('primary_processed', ''),
                roughness=complementary.get('roughness', ''),
                rp02=complementary.get('rp02', ''),
            )
        
        logger.info(f"Found {len(self._file_collections)} test file collections")
        logger.info(f"Found {len(self._file_urls)} file URLs for downloading")
        if self._md_tr_common_checksum:
            logger.info(f"Found MD-TR_Common-to-all.LIS: {self._md_tr_common_checksum}")
    
    async def _parse_common_metadata(self) -> Optional[CommonMetadata]:
        """Parse MD-TR_Common-to-all.LIS for shared metadata.
        
        Returns:
            CommonMetadata or None if not found/failed
        """
        if not self._md_tr_common_checksum:
            return None
        
        content = await self._fetch_file_content(self._md_tr_common_checksum)
        if not content:
            logger.warning("Failed to fetch MD-TR_Common-to-all.LIS")
            return None
        
        # Parse with latin-1 encoding (handles special characters in this file)
        metadata = CommonMetadata()
        
        lines = content.split('\n')
        for line in lines:
            cols = line.split('\t')
            if len(cols) >= 7:
                entry = cols[1].strip().lower()
                information = cols[6].strip().rstrip('\r\n')
                
                if 'material identifier' in entry and information:
                    metadata.material_id = information
                elif 'test standard' in entry and 'applied' not in entry and information:
                    metadata.applicable_standard = information
                elif 'form of as-manufactured material' in entry and information:
                    metadata.form_of_as_manufactured_material = information
                elif 'geometry/size as-manufactured material' in entry and information:
                    metadata.geometry_size_as_manufactured = information
                elif 'geometry/size as-tested material' in entry and information:
                    metadata.geometry_size_as_tested = information
        
        if metadata.material_id:
            logger.info(f"Parsed common metadata: Material={metadata.material_id}, Standard={metadata.applicable_standard}")
        
        return metadata
        
    def group_files_by_test_id(self) -> dict[str, LISFileCollection]:
        """Group files by test ID extracted from filename."""
        return self._file_collections
        
    def find_complementary_files(self) -> ComplementaryFiles:
        """Identify complementary files by filename matching."""
        if not self._complementary_files:
            raise ValueError("No complementary files found. Call load_from_zenodo_graph first.")
        return self._complementary_files
    
    async def get_common_metadata(self) -> Optional[CommonMetadata]:
        """Get parsed common metadata from MD-TR_Common-to-all.LIS.
        
        Returns:
            CommonMetadata or None if not available
        """
        if self._common_metadata is None and self._md_tr_common_checksum:
            self._common_metadata = await self._parse_common_metadata()
        return self._common_metadata
        
    async def _fetch_file_content(self, checksum: str, max_retries: int = 3, initial_delay: float = 1.0) -> Optional[str]:
        """Fetch LIS file content from Zenodo with retry logic and file-based caching.
        
        Caches downloaded files to avoid repeated API calls and rate limiting.
        Cache location: .cache/ in project root.
        
        Args:
            checksum: File checksum (used to lookup URL)
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay before first retry (seconds)
            
        Returns:
            File content as string, or None if fetch fails
        """
        import asyncio
        from fdo_usecases.utils.http_cache import get_cache as get_file_cache
        
        if not self._session:
            self._session = aiohttp.ClientSession()
            
        url = self._file_urls.get(checksum)
        if not url:
            logger.error(f"No URL found for checksum {checksum}. Available URLs: {len(self._file_urls)}")
            return None
        
        # Check file cache first
        file_cache = get_file_cache(ttl_seconds=604800)  # 7 day TTL for file content
        cached_content = file_cache.get(url)
        if cached_content:
            logger.info(f"File cache hit for {checksum}")
            return cached_content
            
        logger.debug(f"Fetching {checksum} from {url[:80]}...")
        
        attempt = 0
        delay = initial_delay
        
        while attempt <= max_retries:
            try:
                async with self._session.get(url) as response:
                    logger.debug(f"Attempt {attempt + 1}/{max_retries + 1}: Response status: {response.status}")
                    
                    # Check status BEFORE reading content
                    if response.status == 429:
                        # Rate limited - retry with exponential backoff
                        retry_after = response.headers.get('Retry-After', str(delay))
                        try:
                            wait_time = float(retry_after)
                        except ValueError:
                            wait_time = delay
                        
                        logger.warning(f"Rate limited (HTTP 429). Waiting {wait_time}s before retry...")
                        await asyncio.sleep(wait_time)
                        attempt += 1
                        delay *= 2  # Exponential backoff
                    elif response.status == 200:
                        # Fetch as bytes first, then decode with error handling
                        content_bytes = await response.read()
                        try:
                            content = content_bytes.decode('utf-8', errors='replace')
                            logger.debug(f"Successfully fetched {len(content)} bytes")
                            
                            # Cache the content
                            try:
                                file_cache.set(url, content)
                            except Exception as e:
                                logger.warning(f"Failed to cache {checksum}: {e}")
                            
                            return content
                        except Exception as e:
                            logger.error(f"Failed to decode content for {checksum}: {e}")
                            return None
                    else:
                        logger.error(f"Failed to fetch {url}: HTTP {response.status}")
                        return None
                        
            except Exception as e:
                logger.error(f"Error fetching {url}: {type(e).__name__}: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(delay)
                    attempt += 1
                    delay *= 2
                else:
                    return None
        
        logger.error(f"Failed to fetch {checksum} after {max_retries + 1} attempts")
        return None
            
    def _parse_date(self, date_str: str, line_num: int, parse_errors: list, test_id: str) -> Optional[datetime]:
        """Parse date string with multiple format support.
        
        Supported formats:
        - "2023-02-08 09:06:15" (ISO-like)
        - "8.2.23 9:06 AM" (US short format with AM/PM)
        - "08.02.2023 09:06" (European format)
        
        Args:
            date_str: Date string to parse
            line_num: Line number for error reporting
            parse_errors: List to append errors to
            test_id: Test ID for logging
            
        Returns:
            datetime object or None if parsing fails
        """
        # Try multiple date formats
        formats = [
            '%Y-%m-%d %H:%M:%S',      # 2023-02-08 09:06:15
            '%d.%m.%y %I:%M %p',       # 8.2.23 9:06 AM
            '%d.%m.%y %H:%M',          # 8.2.23 09:06
            '%d.%m.%Y %H:%M:%S',       # 08.02.2023 09:06:15
            '%d.%m.%Y %H:%M',          # 08.02.2023 09:06
            '%d.%m.%y %I:%M%p',        # 8.2.23 9:06AM (no space)
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # All formats failed
        parse_errors.append(f"Line {line_num}: Invalid date format '{date_str}'")
        logger.warning(f"{test_id}: Could not parse date '{date_str}' with any known format")
        return None
    
    def _parse_lis_content(self, content: str, test_id: str) -> Optional[ParsedTestMetadata]:
        """Parse LIS file content (tab-separated format).
        
        LIS format columns:
        CATEGORIZATION | ENTRY | ADDITIONAL_INFO | SYMBOL | UNIT | REQUIREMENT | INFORMATION | COMMON_TO_ALL
        
        Args:
            content: Raw LIS file content
            test_id: Test identifier for error reporting
            
        Returns:
            ParsedTestMetadata or None on failure
        """
        metadata = {
            'test_id': test_id,
            'project': '',
            'date_test_start': None,
            'date_test_end': None,
            'applicable_standard': '',
            'specified_temperature': 0.0,
            'initial_stress': 0.0,
            'material_id': '',
            'single_crystal_orientation': 0.0,
            'percentage_creep_extension': 0.0,
            'manufacturing_as_manufactured': None,
            'manufacturing_as_tested': None,
            'file_references': [],
        }
        
        # File reference pattern: "See file \"filename.ext\""
        file_ref_pattern = re.compile(r'See file "([^"]+)"', re.IGNORECASE)
        
        lines = content.split('\n')
        parse_errors = []
        
        for line_num, line in enumerate(lines, 1):
            cols = line.split('\t')
            if len(cols) < 7:
                continue
                
            categorization = cols[0].strip()
            entry = cols[1].strip()
            # Strip whitespace including Windows line endings (\r\n)
            information = cols[6].strip().rstrip('\r\n')
            
            # Skip empty or N/A values
            if not information or information.lower() in ['not applicable', 'n/a', '', '-']:
                continue
            
            try:
                # Navigate hierarchy and extract values
                if 'Metadata --> Test info --> Test job details' in categorization:
                    if 'Date of test start' in entry:
                        # Try multiple date formats found in LIS files
                        metadata['date_test_start'] = self._parse_date(information, line_num, parse_errors, test_id)
                    elif 'Date of test end' in entry:
                        metadata['date_test_end'] = self._parse_date(information, line_num, parse_errors, test_id)
                    elif 'Project' in entry:
                        metadata['project'] = information
                    elif 'Test ID' in entry:
                        # Override test_id if different
                        if information and information != test_id:
                            metadata['test_id'] = information
                            
                elif 'Metadata --> Test info --> Test parameters' in categorization:
                    if 'Test standard' in entry and 'applied' not in entry.lower():
                        metadata['applicable_standard'] = information
                    elif 'Specified temperature' in entry:
                        try:
                            metadata['specified_temperature'] = float(information)
                        except ValueError:
                            parse_errors.append(f"Line {line_num}: Invalid temperature value")
                    elif 'Initial stress' in entry:
                        try:
                            metadata['initial_stress'] = float(information)
                        except ValueError:
                            parse_errors.append(f"Line {line_num}: Invalid stress value")
                    elif 'Percentage creep extension' in entry:
                        try:
                            # Convert percentage to ratio (e.g., "1.5%" -> 0.015)
                            value = information.replace('%', '').strip()
                            metadata['percentage_creep_extension'] = float(value) / 100.0
                        except ValueError:
                            parse_errors.append(f"Line {line_num}: Invalid percentage value")
                            
                elif 'Metadata --> Material history and condition' in categorization:
                    if 'Material Identifier' in entry:
                        metadata['material_id'] = information
                    elif 'Single crystal orientation' in entry and 'Determination method' not in categorization:
                        try:
                            # Handle various formats: "6.9°", "6.9", "<001>, 6.9 deg"
                            # Skip descriptive text that doesn't start with a number
                            clean_value = re.sub(r'[°]', '', information).strip()
                            
                            # Check if this looks like actual orientation data (starts with angle or direction)
                            # Pattern: optional direction <XXX> followed by number with degree
                            # Or just a number at the start
                            match = re.match(r'(?:<[\d]+>)?\s*([\d.]+)', clean_value)
                            if match and len(clean_value) < 50:  # Real data is usually short
                                metadata['single_crystal_orientation'] = float(match.group(1))
                            else:
                                # It's descriptive text, not actual orientation value
                                logger.debug(f"{test_id}: Skipping descriptive orientation text: {information[:80]}...")
                                continue  # Skip this line, don't treat as error
                        except (ValueError, AttributeError) as e:
                            logger.warning(f"{test_id}: Line {line_num}: Cannot parse orientation '{information}': {e}")
                            parse_errors.append(f"Line {line_num}: Invalid orientation value '{information}' - {str(e)}")
                    elif 'Manufacturing process description as-manufactured material' in categorization:
                        metadata['manufacturing_as_manufactured'] = information
                    elif 'Manufacturing process description as-tested material' in categorization:
                        metadata['manufacturing_as_tested'] = information
                        
                # Extract file references from any field
                file_refs = file_ref_pattern.findall(information)
                metadata['file_references'].extend(file_refs)
                
            except Exception as e:
                parse_errors.append(f"Line {line_num}: {str(e)}")
                continue
        
        # Log parse errors as warnings
        if parse_errors:
            for error in parse_errors[:5]:  # Limit to first 5 errors
                logger.warning(f"{test_id}: {error}")
            if len(parse_errors) > 5:
                logger.warning(f"{test_id}: ... and {len(parse_errors) - 5} more parse errors")
        
        # Validate required fields
        if not metadata['date_test_start'] or not metadata['date_test_end']:
            logger.warning(f"Missing dates for {test_id}")
            return None
        
        # Note: applicable_standard and material_id may come from MD-TR_Common-to-all.LIS
        # so we don't fail here if they're missing from individual test files
        
        if not metadata['material_id']:
            logger.debug(f"No material ID in {test_id} (may be in Common-to-all file)")
        
        if not metadata['applicable_standard']:
            logger.debug(f"No test standard in {test_id} (may be in Common-to-all file)")
        
        # Remove duplicates from file references
        metadata['file_references'] = list(set(metadata['file_references']))
        
        return ParsedTestMetadata(**metadata)
        
    async def parse_md_tr_file(self, checksum: str) -> Optional[ParsedTestMetadata]:
        """Parse MD-TR.lis file content.
        
        Fetches file from Zenodo and parses tab-separated content.
        Returns None on parse failure (soft fail).
        
        Args:
            checksum: File checksum to fetch
            
        Returns:
            ParsedTestMetadata or None on failure
        """
        try:
            # Extract test ID from checksum by searching collections
            test_id = "unknown"
            for tid, collection in self._file_collections.items():
                if collection.md_tr_checksum == checksum:
                    test_id = tid
                    break
            
            logger.info(f"Parsing MD-TR file for {test_id} (checksum: {checksum})")
            
            # Fetch file content
            content = await self._fetch_file_content(checksum)
            if not content:
                logger.error(f"Failed to fetch content for {test_id}: checksum={checksum}")
                self._errors.append(ParsingError(
                    test_id=test_id,
                    filename=checksum,
                    error_type="FETCH_ERROR",
                    message=f"Failed to download file from Zenodo (URL lookup failed)",
                ))
                return None
                
            # Parse content
            logger.debug(f"Parsing {len(content)} bytes for {test_id}")
            metadata = self._parse_lis_content(content, test_id)
            if not metadata:
                logger.error(f"Failed to parse LIS content for {test_id}")
                self._errors.append(ParsingError(
                    test_id=test_id,
                    filename=checksum,
                    error_type="PARSE_ERROR",
                    message="Failed to parse LIS content",
                ))
                return None
                
            logger.info(f"Successfully parsed {test_id}: material={metadata.material_id}, temp={metadata.specified_temperature}°C, stress={metadata.initial_stress}MPa")
            return metadata
            
        except Exception as e:
            logger.exception(f"Failed to parse MD-TR file {checksum}: {type(e).__name__}: {e}")
            self._errors.append(ParsingError(
                test_id="unknown",
                filename=checksum,
                error_type="EXCEPTION",
                message=f"{type(e).__name__}: {str(e)}",
            ))
            return None
            
    def find_sem_images(self) -> list[str]:
        """Find SEM .tiff image checksums from Zenodo graph.
        
        Searches for files with:
        - MIME type 'image/tiff' or 'image/tif'
        - Filename extensions .tif or .tiff
        - Keywords in filename: 'SEM', 'dendrite', 'microstructure'
        
        Returns:
            List of checksums for .tiff files
        """
        sem_checksums = []
        
        # Pattern for SEM-related filenames
        sem_pattern = re.compile(r'(SEM|dendrite|microstructure|interdentritic)', re.IGNORECASE)
        
        # We need to search the graph - but we don't have direct access here
        # This method should be called after load_from_zenodo_graph
        # For now, return empty - the orchestrator will populate this from the graph
        return sem_checksums
        
    def find_preview_images(self) -> list[str]:
        """Find preview .jpg image URLs from Zenodo graph.
        
        Searches for files with:
        - MIME type 'image/jpeg' or 'image/jpg'
        - Filename extensions .jpg or .jpeg
        - Keywords: 'location', 'optical', 'overview', 'test-piece'
        
        Returns:
            List of download URLs for .jpg files
        """
        preview_urls = []
        
        # Pattern for preview image filenames
        preview_pattern = re.compile(r'(location|optical|overview|test[- ]piece)', re.IGNORECASE)
        
        # We need to search the graph - but we don't have direct access here
        # This method should be called after load_from_zenodo_graph
        # For now, return empty - the orchestrator will populate this from the graph
        return preview_urls
    
    def extract_images_from_graph(self, zenodo_graph: dict) -> tuple[list[str], list[str]]:
        """Extract SEM and preview image information from Zenodo graph.
        
        Args:
            zenodo_graph: Pre-populated graph from ZenodoFDODesign
            
        Returns:
            Tuple of (sem_checksums, preview_urls)
        """
        sem_checksums = []
        preview_urls = []
        
        sem_pattern = re.compile(r'(SEM|dendrite|microstructure|interdentritic)', re.IGNORECASE)
        preview_pattern = re.compile(r'(location|optical|overview|test[- ]piece)', re.IGNORECASE)
        tif_pattern = re.compile(r'\.tif$', re.IGNORECASE)
        jpg_pattern = re.compile(r'\.jpe?g$', re.IGNORECASE)
        
        for record_id, record in zenodo_graph.items():
            # Convert PidRecord to dict
            record_dict = record.toSimpleJSON()
            
            # Extract filename
            name_attrs = [attr['value'] for attr in record_dict['record'] 
                         if attr['key'] == '21.T11969/bd3e9fb9b606d2198c9e']
            if not name_attrs:
                continue
            filename = name_attrs[0]
            
            # Extract MIME type
            mime_attrs = [attr['value'] for attr in record_dict['record']
                         if attr['key'] == '21.T11969/3313b863118ed5eb0ded']
            mime_type = mime_attrs[0].lower() if mime_attrs else ''
            
            # Extract download URL
            url_attrs = [attr['value'] for attr in record_dict['record']
                        if attr['key'] == '21.T11969/479febb2bbe8400da547']
            download_url = url_attrs[0] if url_attrs else None
            
            # Check for SEM images (.tiff files with SEM-related names)
            if tif_pattern.search(filename) or 'image/tiff' in mime_type:
                if sem_pattern.search(filename):
                    sem_checksums.append(record_id)
                    logger.debug(f"Found SEM image: {filename} ({record_id})")
            
            # Check for preview images (.jpg files with preview-related names)
            if jpg_pattern.search(filename) or 'image/jpeg' in mime_type:
                if preview_pattern.search(filename):
                    if download_url:
                        preview_urls.append(download_url)
                        logger.debug(f"Found preview image: {filename}")
        
        logger.info(f"Found {len(sem_checksums)} SEM images and {len(preview_urls)} preview images")
        return sem_checksums, preview_urls
        
    def get_creators_from_dataset(self, zenodo_graph: dict) -> list[str]:
        """Extract creator ORCIDs from Dataset FDO.
        
        Args:
            zenodo_graph: Pre-populated graph
            
        Returns:
            List of creator ORCID URLs
        """
        creators = []
        for record_id, record in zenodo_graph.items():
            # Convert PidRecord to dict
            record_dict = record.toSimpleJSON()
            # Look for creator attributes
            creator_attrs = [attr['value'] for attr in record_dict['record']
                           if attr['key'] == '21.T11969/7c67083a5d218e544063']
            creators.extend(creator_attrs)
        
        return list(set(creators))  # Deduplicate
        
    def get_creator_affiliations_from_dataset(self, zenodo_graph: dict) -> list[str]:
        """Extract ROR IDs from Dataset FDO.
        
        Args:
            zenodo_graph: Pre-populated graph
            
        Returns:
            List of ROR ID URLs
        """
        affiliations = []
        for record_id, record in zenodo_graph.items():
            # Convert PidRecord to dict
            record_dict = record.toSimpleJSON()
            # Look for creatorAffiliation attributes
            aff_attrs = [attr['value'] for attr in record_dict['record']
                        if attr['key'] == '21.T11969/ea9f6b3d78c6608fe801']
            affiliations.extend(aff_attrs)
        
        return list(set(affiliations))  # Deduplicate
        
    def get_keywords_from_dataset(self, zenodo_graph: dict) -> list[str]:
        """Extract keywords from Dataset FDO.
        
        Args:
            zenodo_graph: Pre-populated graph
            
        Returns:
            List of keywords
        """
        keywords = []
        for record_id, record in zenodo_graph.items():
            # Convert PidRecord to dict
            record_dict = record.toSimpleJSON()
            # Look for keyword attributes
            kw_attrs = [attr['value'] for attr in record_dict['record']
                       if attr['key'] == '21.T11969/793ff5c33c3aeb32907a']
            keywords.extend(kw_attrs)
        
        return list(set(keywords))  # Deduplicate
        
    def extract_keywords(self, metadata: ParsedTestMetadata) -> list[str]:
        """Extract domain keywords from metadata.
        
        Args:
            metadata: Parsed test metadata
            
        Returns:
            List of domain-specific keywords
        """
        keywords = []
        
        # From material ID
        if metadata.material_id:
            keywords.append(metadata.material_id)
        
        # From test standard
        if metadata.applicable_standard:
            # Extract just the standard number
            std_part = metadata.applicable_standard.split(':')[0]
            keywords.append(std_part)
        
        # From test type (if available)
        # Could add more extraction logic here
        
        return list(set(keywords))
        
    @property
    def errors(self) -> list[ParsingError]:
        """Get list of parsing errors."""
        return self._errors
        
    def report_errors(self) -> None:
        """Log all parsing errors."""
        if self._errors:
            logger.error(f"LIS parsing encountered {len(self._errors)} error(s):")
            for error in self._errors:
                logger.error(f"  [{error.error_type}] {error.test_id}/{error.filename}: {error.message}")
