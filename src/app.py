import os
from flask import Flask, jsonify, request
from flask_migrate import Migrate
from flask_cors import CORS
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from utils import APIException, generate_sitemap
from admin import setup_admin
from models import db, User, Character, Planet, Favorite

app = Flask(__name__)
app.url_map.strict_slashes = False

# DB CONFIG
db_url = os.getenv("DATABASE_URL")

if db_url:
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url.replace(
        "postgres://", "postgresql://")
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///starwars.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
Migrate(app, db)
CORS(app)
setup_admin(app)


# ERROR HANDLER
@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code


@app.route("/")
def sitemap():
    return generate_sitemap(app)


# USER SIMULADO
CURRENT_USER_ID = 1


def get_current_user():
    return db.session.get(User, CURRENT_USER_ID)


# CHARACTERS
@app.route("/characters", methods=["GET"])
def get_characters():
    characters = db.session.execute(select(Character)).scalars().all()
    return jsonify([c.serialize() for c in characters]), 200


@app.route("/characters/<int:character_id>", methods=["GET"])
def get_single_character(character_id):
    character = db.session.get(Character, character_id)

    if not character:
        return jsonify({"msg": "Character not found"}), 404

    return jsonify(character.serialize()), 200


# PLANETS
@app.route("/planets", methods=["GET"])
def get_planets():
    planets = db.session.execute(select(Planet)).scalars().all()
    return jsonify([p.serialize() for p in planets]), 200


@app.route("/planets/<int:planet_id>", methods=["GET"])
def get_single_planet(planet_id):
    planet = db.session.get(Planet, planet_id)

    if not planet:
        return jsonify({"msg": "Planet not found"}), 404

    return jsonify(planet.serialize()), 200


# USERS
@app.route("/users", methods=["GET"])
def get_users():
    users = db.session.execute(select(User)).scalars().all()
    return jsonify([u.serialize() for u in users]), 200


@app.route("/users/favorites", methods=["GET"])
def get_user_favorites():
    user = get_current_user()

    if not user:
        return jsonify({"msg": "User not found"}), 404

    return jsonify([fav.serialize() for fav in user.favorites]), 200


# CREATE CHARACTER
@app.route("/characters", methods=["POST"])
def create_character():
    body = request.get_json(silent=True)

    if not isinstance(body, dict):
        return jsonify({"msg": "Invalid JSON body"}), 400

    if not body:
        return jsonify({"msg": "Request body is required"}), 400

    if "name" not in body:
        return jsonify({"msg": "Name is required"}), 400

    try:
        new_character = Character(
            name=body["name"],
            gender=body.get("gender"),
            birth_year=body.get("birth_year"),
            description=body.get("description")
        )

        db.session.add(new_character)
        db.session.commit()

        return jsonify(new_character.serialize()), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({"msg": "Duplicate or invalid data"}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e)}), 500


# CREATE PLANET
@app.route("/planets", methods=["POST"])
def create_planet():
    body = request.get_json(silent=True)

    if not isinstance(body, dict):
        return jsonify({"msg": "Invalid JSON body"}), 400

    if not body:
        return jsonify({"msg": "Request body is required"}), 400

    if "name" not in body:
        return jsonify({"msg": "Name is required"}), 400

    try:
        new_planet = Planet(
            name=body["name"],
            climate=body.get("climate"),
            population=body.get("population"),
            description=body.get("description")
        )

        db.session.add(new_planet)
        db.session.commit()

        return jsonify(new_planet.serialize()), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({"msg": "Duplicate or invalid data"}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e)}), 500


# FAVORITES
@app.route("/favorite/planet/<int:planet_id>", methods=["POST"])
def add_favorite_planet(planet_id):
    user = get_current_user()
    if not user:
        return jsonify({"msg": "User not found"}), 404

    planet = db.session.get(Planet, planet_id)
    if not planet:
        return jsonify({"msg": "Planet not found"}), 404

    existing = db.session.execute(
        select(Favorite).filter_by(user_id=user.id, planet_id=planet_id)
    ).scalar_one_or_none()

    if existing:
        return jsonify({"msg": "Already in favorites"}), 400

    try:
        fav = Favorite(user_id=user.id, planet_id=planet_id)
        db.session.add(fav)
        db.session.commit()
        return jsonify(fav.serialize()), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({"msg": "Already in favorites"}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e)}), 500


@app.route("/favorite/character/<int:character_id>", methods=["POST"])
def add_favorite_character(character_id):
    user = get_current_user()
    if not user:
        return jsonify({"msg": "User not found"}), 404

    character = db.session.get(Character, character_id)
    if not character:
        return jsonify({"msg": "Character not found"}), 404

    existing = db.session.execute(
        select(Favorite).filter_by(user_id=user.id, character_id=character_id)
    ).scalar_one_or_none()

    if existing:
        return jsonify({"msg": "Already in favorites"}), 400

    try:
        fav = Favorite(user_id=user.id, character_id=character_id)
        db.session.add(fav)
        db.session.commit()
        return jsonify(fav.serialize()), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({"msg": "Already in favorites"}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e)}), 500


# DELETE FAVORITES
@app.route("/favorite/planet/<int:planet_id>", methods=["DELETE"])
def delete_favorite_planet(planet_id):
    user = get_current_user()
    if not user:
        return jsonify({"msg": "User not found"}), 404

    fav = db.session.execute(
        select(Favorite).filter_by(user_id=user.id, planet_id=planet_id)
    ).scalar_one_or_none()

    if not fav:
        return jsonify({"msg": "Favorite not found"}), 404

    db.session.delete(fav)
    db.session.commit()

    return jsonify({"msg": "Deleted successfully"}), 200


@app.route("/favorite/character/<int:character_id>", methods=["DELETE"])
def delete_favorite_character(character_id):
    user = get_current_user()
    if not user:
        return jsonify({"msg": "User not found"}), 404

    fav = db.session.execute(
        select(Favorite).filter_by(user_id=user.id, character_id=character_id)
    ).scalar_one_or_none()

    if not fav:
        return jsonify({"msg": "Favorite not found"}), 404

    db.session.delete(fav)
    db.session.commit()

    return jsonify({"msg": "Deleted successfully"}), 200


if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=PORT, debug=True)


# """
# This module takes care of starting the API Server, Loading the DB and Adding the endpoints
# """
# import os
# from flask import Flask, request, jsonify, url_for
# from flask_migrate import Migrate
# from flask_swagger import swagger
# from flask_cors import CORS
# from utils import APIException, generate_sitemap
# from admin import setup_admin
# from models import db, User
# #from models import Person

# app = Flask(__name__)
# app.url_map.strict_slashes = False

# db_url = os.getenv("DATABASE_URL")
# if db_url is not None:
#     app.config['SQLALCHEMY_DATABASE_URI'] = db_url.replace("postgres://", "postgresql://")
# else:
#     app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:////tmp/test.db"
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# MIGRATE = Migrate(app, db)
# db.init_app(app)
# CORS(app)
# setup_admin(app)

# # Handle/serialize errors like a JSON object
# @app.errorhandler(APIException)
# def handle_invalid_usage(error):
#     return jsonify(error.to_dict()), error.status_code

# # generate sitemap with all your endpoints
# @app.route('/')
# def sitemap():
#     return generate_sitemap(app)

# @app.route('/user', methods=['GET'])
# def handle_hello():

#     response_body = {
#         "msg": "Hello, this is your GET /user response "
#     }

#     return jsonify(response_body), 200

# # this only runs if `$ python src/app.py` is executed
# if __name__ == '__main__':
#     PORT = int(os.environ.get('PORT', 3000))
#     app.run(host='0.0.0.0', port=PORT, debug=False)
