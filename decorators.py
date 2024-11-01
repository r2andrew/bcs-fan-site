import string
from flask import request, jsonify, make_response
import pymongo.errors
import jwt
from functools import wraps
import globals
from bson import ObjectId

blacklist = globals.db.blacklist
episodes = globals.db.episodes

def jwt_required(func):
    @wraps(func)
    def jwt_required_wrapper(*args, **kwargs):
        token = None
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        if not token:
            return make_response(jsonify(
                {'message' : 'Token is missing'}), 401)
        try:
            bl_token = blacklist.find_one({"token": token})
        except pymongo.errors.ServerSelectionTimeoutError:
            return make_response(jsonify({"error": "Connection to database timed out"}), 500)
        except:
            return make_response(jsonify({"error": "An unknown error occurred in the database"}), 500)
        if bl_token is not None:
            return make_response(jsonify({
                'message': 'Token has been cancelled'}), 401)
        try:
            token = jwt.decode(token,
                globals.secret_key,
                algorithms="HS256")
        except:
            return make_response(jsonify(
                {'message' : 'Token is invalid'}), 401)
        return func(token, *args, **kwargs)
    return jwt_required_wrapper

def admin_required(func):
    @wraps(func)
    def admin_required_wrapper(*args, **kwargs):
        token = request.headers['x-access-token']
        data = jwt.decode(
            token, globals.secret_key, algorithms="HS256")
        if data["admin"]:
            return func(*args, **kwargs)
        else:
            return make_response(jsonify( {
                'message' : 'Admin access required' } ), 401 )
    return admin_required_wrapper

def original_poster_required(func):
    @wraps(func)
    def original_poster_required_wrapper(*args, **kwargs):
        token = request.headers['x-access-token']
        user = jwt.decode(token, globals.secret_key, algorithms="HS256")["user"]
        tid = request.base_url.split('/')[-1]
        if not all(c in string.hexdigits for c in tid):
            return make_response(jsonify({"error": "Invalid trivia id format"}), 422)
        try:
            original_post = episodes.find_one({ "trivias._id" : ObjectId(tid)},
                                                {"trivias" : {"$elemMatch" : {"_id" : ObjectId(tid)}}})
            original_poster = original_post["trivias"][0]["user"]
        except pymongo.errors.ServerSelectionTimeoutError:
            return make_response(jsonify({"error": "Connection to database timed out"}), 500)
        except KeyError:
            return make_response(jsonify({"error": "No matching documents for that tid"}), 404)
        except:
            return make_response(jsonify({"error": "An unknown error occurred in the database" }), 500)
        if user == original_poster:
            return func(*args, **kwargs)
        else:
            return make_response(jsonify({
                'message': 'This item may only be edited by the original user'}), 401)
    return original_poster_required_wrapper