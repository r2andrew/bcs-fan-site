from flask import Blueprint, request, make_response, jsonify
import pymongo.errors
import globals
from decorators import jwt_required
import bcrypt
import jwt
import datetime

auth_bp = Blueprint("auth_bp", __name__)

users = globals.db.users
blacklist = globals.db.blacklist

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
            if bcrypt.checkpw(bytes(auth.password, 'UTF-8'),
                user["password"]):
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
                'message': 'Bad username'}), 401)

    return make_response(jsonify({
        'message': 'Authentication required'}), 401)

@auth_bp.route('/api/v1.0/logout', methods=["GET"])
@jwt_required
def logout():
    token = request.headers['x-access-token']
    try:
        blacklist.insert_one({"token":token})
    except pymongo.errors.ServerSelectionTimeoutError:
        return make_response(jsonify({"error": "Connection to database timed out"}), 500)
    except pymongo.errors:
        return make_response(jsonify({"error": "An unknown error occurred in the database"}), 500)
    return make_response(jsonify( {
        'message' : 'Logout successful' } ), 200 )