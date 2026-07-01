# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache2.0

"""CLI of fdo-usecases."""

import typer

from fdo_usecases.lib import CalcOperation, calculate

# create subcommand app
say = typer.Typer()

# create main app
app = typer.Typer()
app.add_typer(say, name="say")

# ----


@app.command()
def calc(op: CalcOperation, x: int, y: int):
    """Compute the result of applying an operation on x and y."""
    result: int = calculate(op, x, y)
    typer.echo(f"Result: {result}")


# ----


@say.command()
def hello(name: str):
    """Greet a person."""
    print(f"Hello {name}")


@say.command()
def goodbye(name: str, formal: bool = False):
    """Say goodbye to a person."""
    if formal:
        print(f"Goodbye {name}. Have a good day.")
    else:
        print(f"Bye {name}!")
