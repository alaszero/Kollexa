#!/usr/bin/env python
"""Comandos CLI de administración de Kollexa."""
import os
import sys
import click
from app import create_app

app = create_app(os.getenv('FLASK_ENV', 'development'))


@app.cli.command('seed')
def seed_command():
    """Poblar base de datos con datos iniciales."""
    from scripts.seed import run_seed
    run_seed(app)
    click.echo('Seed completado.')


@app.cli.command('create-admin')
@click.option('--username', prompt=True)
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
@click.option('--email', prompt=True)
def create_admin_command(username, password, email):
    """Crear un usuario administrador."""
    from scripts.seed import create_admin_user
    with app.app_context():
        user = create_admin_user(username, password, email)
        if user:
            click.echo(f'Admin "{username}" creado exitosamente.')
        else:
            click.echo(f'Error: el usuario "{username}" ya existe.', err=True)


@app.cli.command('version')
def version_command():
    """Mostrar versión actual."""
    click.echo(f'Kollexa v{app.config["VERSION"]}')


if __name__ == '__main__':
    with app.app_context():
        from app.extensions import db
        db.create_all()
