import string
from flask import Blueprint, request, make_response, jsonify
import globals
import pymongo.errors
from bson import ObjectId

users_bp = Blueprint("users_bp", __name__)

users = globals.db.users

@users_bp.route("/api/v1.0/users/<string:uid>", methods=["GET"])
def get_user(uid):
    if not all(c in string.hexdigits for c in uid):
        return make_response(jsonify({"error" : "Invalid id format"} ), 422)
    try:
        user = users.find_one({'_id': ObjectId(uid)}, {"password":0, "_id": 0})
    except pymongo.errors.ServerSelectionTimeoutError:
        return make_response(jsonify({"error" : "Connection to database timed out"} ), 500)
    except:
        return make_response(jsonify({"error" : "An unknown error occurred in the database"}), 500)
    if user is not None:
        return make_response( jsonify( user ), 200 )
    else:
        return make_response( jsonify({"error" : "Invalid episode ID"} ), 404 )
