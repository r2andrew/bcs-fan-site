from flask import Blueprint, request, make_response, jsonify
import globals
import pymongo.errors

users_bp = Blueprint("users_bp", __name__)

users = globals.db.users

@users_bp.route("/api/v1.0/users/<string:username>", methods=["GET"])
def get_user(username):
    try:
        user = users.find_one({'username': username}, {"password":0})
    except pymongo.errors.ServerSelectionTimeoutError:
        return make_response(jsonify({"error" : "Connection to database timed out"} ), 500)
    except:
        return make_response(jsonify({"error" : "An unknown error occurred in the database"}), 500)
    if user is not None:
        user["_id"] = str(user["_id"])
        return make_response( jsonify( user ), 200 )
    else:
        return make_response( jsonify({"error" : "Invalid episode ID"} ), 404 )
