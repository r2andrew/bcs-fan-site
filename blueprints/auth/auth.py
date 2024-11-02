from flask import Blueprint, request, make_response, jsonify
import pymongo.errors
import globals
from decorators import jwt_required, admin_required
import bcrypt
import jwt
import datetime
from bson import ObjectId
import re
import string

auth_bp = Blueprint("auth_bp", __name__)

users = globals.db.users
blacklist = globals.db.blacklist

@auth_bp.route("/api/v1.0/register", methods=["POST"])
def register():
    if "name" in request.form and "username" in request.form and "password" in request.form and "email" in request.form:
        if re.match(r"[^@]+@[^@]+\.[^@]+", request.form["email"]):
            try:
                existing_user = users.find_one({'username': request.form["username"]})
            except pymongo.errors.ServerSelectionTimeoutError:
                return make_response(jsonify({"error": "Connection to database timed out"}), 500)
            except pymongo.errors:
                return make_response(jsonify({"error": "An unknown error occurred in the database"}), 500)
            if not existing_user:
                password = request.form["password"].encode("utf-8")
                new_user = {
                    "_id" : ObjectId(),
                    "name": str(request.form["name"]),
                    "username" : str(request.form["username"]),
                    "password" : bcrypt.hashpw(password, bcrypt.gensalt()),
                    "email" : str(request.form["email"]),
                    "admin": False,
                    "banned": False
                }
                try:
                    users.insert_one(new_user)
                except pymongo.errors.ServerSelectionTimeoutError:
                    return make_response(jsonify({"error": "Connection to database timed out"}), 500)
                except:
                    return make_response(jsonify({"error": "An unknown error occurred in the database"}), 500)
                return make_response(jsonify({"message": "User created"}), 201)
            else:
                return make_response(jsonify({"message": "Username taken"}), 409)
        else:
            return make_response(jsonify({"error": "Invalid email format"}), 422)
    else:
        return make_response( jsonify({ "error" : "Missing form data" } ), 404)

@auth_bp.route('/api/v1.0/login', methods=['GET'])
def login():
    auth = request.authorization
    if auth:
        try:
            user = users.find_one({'username': auth.username})
        except pymongo.errors.ServerSelectionTimeoutError:
            return make_response(jsonify({"error": "Connection to database timed out"}), 500)
        except pymongo.errors:
            return make_response(jsonify({"error": "An unknown error occurred in the database"}), 500)
        if user is not None:
            if not user["banned"]:
                if bcrypt.checkpw(bytes(auth.password, 'UTF-8'), user["password"]):
                        token = jwt.encode( {
                            'user' : auth.username,
                            'admin' : user['admin'],
                            'exp' : datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30) },
                            globals.secret_key,
                            algorithm="HS256")
                        return make_response(jsonify({'token' : token}), 200)
                else:
                    return make_response(jsonify({
                        'message': 'Bad password'}), 401)
            else:
                return make_response(jsonify({
                    'message': 'User banned'}), 401)
        else:
            return make_response(jsonify({
                'message': 'Bad username'}), 401)

    return make_response(jsonify({
        'message': 'Authentication required'}), 401)

@auth_bp.route('/api/v1.0/logout', methods=["GET"])
@jwt_required
def logout(token):
    token = request.headers['x-access-token']
    try:
        blacklist.insert_one({"token":token})
    except pymongo.errors.ServerSelectionTimeoutError:
        return make_response(jsonify({"error": "Connection to database timed out"}), 500)
    except pymongo.errors:
        return make_response(jsonify({"error": "An unknown error occurred in the database"}), 500)
    return make_response(jsonify( {
        'message' : 'Logout successful' } ), 200 )

@auth_bp.route("/api/v1.0/ban/<uid>", methods=["PATCH"])
@jwt_required
@admin_required
def delete_user(token, uid):
    if not all(c in string.hexdigits for c in uid):
        return make_response(jsonify({"error" : "Invalid user id format"} ), 422)
    edited_user = {
        "name": "banned",
        "banned": True,
    }
    try:
        users.update_one({ "_id" : ObjectId(uid) }, { "$set" : edited_user })
    except pymongo.errors.ServerSelectionTimeoutError:
        return make_response(jsonify({"error": "Connection to database timed out"}), 500)
    except:
        return make_response(jsonify({"error": "An unknown error occurred in the database"}), 500)
    return make_response(jsonify({"message": "User banned"}), 200)
