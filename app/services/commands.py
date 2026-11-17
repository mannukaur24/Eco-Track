"""Flask CLI commands for EcoTrack database administration.

Registered in the application factory. These commands are used during
development to seed reference data and create the first administrator
account. No default or publicly known password is ever created.
"""

import click
from flask.cli import with_appcontext
from app.extensions import db
from app.models.user import User, Role
from app.models.waste_category import WasteCategory
from app.models.awareness_article import AwarenessArticle
from app.utils.datetime import utc_now


def _seed_waste_categories():
    """Insert the default waste categories that are missing from the DB.

    Existing category records are preserved; only categories whose name is not
    already present are inserted. Newly created categories are active by
    default so they appear in the Citizen Portal complaint form.
    """
    categories = [
        ("Plastic Waste", "Bottles, bags, packaging and other plastic items."),
        ("Organic Waste", "Kitchen scraps, food waste, garden waste."),
        ("Electronic Waste", "Electronic items, batteries, cables."),
        ("Household Waste", "Everyday household rubbish and trash."),
        ("Construction Waste", "Debris from construction and demolition work."),
        ("Industrial Waste", "Waste generated from industrial and factory processes."),
        ("Other", "Any other type of waste not listed above."),
    ]
    count = 0
    for name, description in categories:
        if not WasteCategory.query.filter_by(category_name=name).first():
            db.session.add(
                WasteCategory(category_name=name, description=description, is_active=True)
            )
            count += 1
    db.session.commit()
    return count


def _seed_awareness_articles():
    articles = [
        (
            "Segregate Waste at Source",
            "Separate organic, recyclable and hazardous waste at home to make "
            "collection and recycling more effective.",
            "Segregation",
        ),
        (
            "Reduce Single-Use Plastics",
            "Carry reusable bags, bottles and containers to cut down plastic waste.",
            "Reduction",
        ),
        (
            "Compost Kitchen Waste",
            "Turn fruit and vegetable peels into compost for home gardening.",
            "Organic Waste",
        ),
        (
            "Recycle Paper and Cardboard",
            "Keep paper dry and clean so it can be recycled into new products.",
            "Recycling",
        ),
        (
            "Dispose of E-Waste Safely",
            "Hand over old phones, batteries and electronics to authorized e-waste "
            "centres instead of throwing them in the bin.",
            "E-Waste",
        ),
    ]
    count = 0
    now = utc_now()
    for title, content, topic in articles:
        if not AwarenessArticle.query.filter_by(title=title).first():
            db.session.add(
                AwarenessArticle(
                    title=title,
                    content=content,
                    topic=topic,
                    is_published=True,
                    published_at=now,
                )
            )
            count += 1
    db.session.commit()
    return count


@click.command("seed-db")
@with_appcontext
def seed_db():
    """Seed default waste categories and awareness articles."""
    cats = _seed_waste_categories()
    arts = _seed_awareness_articles()
    click.echo(f"Seeded {cats} waste categories and {arts} awareness articles.")


@click.command("seed-categories")
@with_appcontext
def seed_categories():
    """Seed missing default waste categories into the configured database.

    Inserts only categories that do not already exist, so it is safe to run
    repeatedly. Newly created categories are active by default.
    """
    count = _seed_waste_categories()
    click.echo(f"Seeded {count} missing waste category/categories.")


@click.command("create-admin")
@click.option("--email", prompt="Admin email", help="Administrator email address")
@click.option("--full-name", prompt="Full name", help="Administrator full name")
@click.option("--password", prompt="Password", hide_input=True,
              confirmation_prompt=True, help="Administrator password")
@with_appcontext
def create_admin(email, full_name, password):
    """Create the first administrator account interactively.

    The password is prompted and never stored in plain text or in the command
    history. No default password is used.
    """
    email = email.strip().lower()
    if User.query.filter_by(email=email).first():
        click.echo(f"An account with email {email} already exists.")
        return

    admin = User(
        full_name=full_name.strip(),
        email=email,
        role=Role.ADMINISTRATOR,
        is_active=True,
    )
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    click.echo(f"Administrator account created: {email}")
