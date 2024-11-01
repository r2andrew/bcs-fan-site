from datetime import datetime

import pymongo.errors
from flask import Blueprint, request, make_response, jsonify
import string
from bson import ObjectId
from decorators import jwt_required, admin_required, original_poster_required
import globals

trivias_bp = Blueprint("trivias_bp", __name__)

episodes = globals.db.episodes

@trivias_bp.route("/api/v1.0/episodes/<string:id>/trivias", methods=["POST"])
@jwt_required
def add_new_trivia(token, id):
    if not all(c in string.hexdigits for c in id):
        return make_response(jsonify({"error" : "Invalid id format"} ), 422)
    if "text" in request.form:
        new_trivia = {
            "_id" : ObjectId(),
            "createdDtm": datetime.utcnow(),
            "modifiedDtm": datetime.utcnow(),
            "user" : token["user"],
            "text" : request.form["text"],
            "score" : 0
        }
        try:
            episodes.update_one( { "_id" : ObjectId(id) }, { "$push": { "trivias" : new_trivia } } )
        except pymongo.errors.ServerSelectionTimeoutError:
            return make_response(jsonify({"error": "Connection to database timed out"}), 500)
        except:
            return make_response(jsonify({"error": "An unknown error occurred in the database"}), 500)
        new_trivia_link = "http://localhost:5000/api/v1.0/episodes/" \
        + id +"/trivias/" + str(new_trivia['_id'])
        return make_response( jsonify( { "url" : new_trivia_link } ), 201 )
    else:
        return make_response( jsonify({ "error" : "Missing form data" } ), 404)

@trivias_bp.route("/api/v1.0/episodes/<string:id>/trivias", methods=["GET"])
def fetch_all_trivias(id):
    if not all(c in string.hexdigits for c in id):
        return make_response(jsonify({"error" : "Invalid id format"} ), 422)
    data_to_return = []
    try:
        episode = episodes.find_one( { "_id" : ObjectId(id) }, { "trivias" : 1, "_id" : 0 } )
    except pymongo.errors.ServerSelectionTimeoutError:
        return make_response(jsonify({"error": "Connection to database timed out"}), 500)
    except:
        return make_response(jsonify({"error": "An unknown error occurred in the database"}), 500)
    for trivia in episode["trivias"]:
        trivia["_id"] = str(trivia["_id"])
        data_to_return.append(trivia)
    return make_response( jsonify( data_to_return ), 200 )

@trivias_bp.route("/api/v1.0/episodes/<eid>/trivias/<tid>", methods=["GET"])
def fetch_one_trivia(eid, tid):
    if not all(c in string.hexdigits for c in eid):
        return make_response(jsonify({"error" : "Invalid episode id format"} ), 422)
    if not all(c in string.hexdigits for c in tid):
        return make_response(jsonify({"error" : "Invalid trivia id format"} ), 422)
    try:
        episode = episodes.find_one({ "trivias._id" : ObjectId(tid) },
        { "_id" : 0, "trivias.$" : 1 } )
    except pymongo.errors.ServerSelectionTimeoutError:
        return make_response(jsonify({"error": "Connection to database timed out"}), 500)
    except:
        return make_response(jsonify({"error": "An unknown error occurred in th1e database"}), 500)
    if episode is None:
        return make_response(jsonify({"error":"Invalid episode ID or trivia ID"}),404)
    episode['trivias'][0]['_id'] = str(episode['trivias'][0]['_id'])
    return make_response( jsonify(episode['trivias'][0]), 200)

@trivias_bp.route("/api/v1.0/episodes/<eid>/trivias/<tid>", methods=["PATCH"])
@jwt_required
@original_poster_required
def edit_trivia(token, eid, tid):
    if not all(c in string.hexdigits for c in eid):
        return make_response(jsonify({"error" : "Invalid episode id format"} ), 422)
    if "text" in request.form:
        edited_trivia = {
            "trivias.$.modifiedDtm" : datetime.utcnow(),
            "trivias.$.text" : request.form["text"],
        }
        try:
            episodes.update_one( { "trivias._id" : ObjectId(tid) }, { "$set" : edited_trivia } )
        except pymongo.errors.ServerSelectionTimeoutError:
            return make_response(jsonify({"error": "Connection to database timed out"}), 500)
        except:
            return make_response(jsonify({"error": "An unknown error occurred in the database"}), 500)
        edit_trivia_url = "http://localhost:5000/api/v1.0/episodes/" + \
        eid + "/trivias/" + tid
        return make_response( jsonify( {"url":edit_trivia_url} ), 200)
    else:
        return make_response(jsonify({"error": "Missing form data"}), 404)

@trivias_bp.route("/api/v1.0/episodes/<string:id>/trivias/<tid>/vote", methods=["PATCH"])
@jwt_required
def vote_on_trivia(token, id, tid):
    if not all(c in string.hexdigits for c in id):
        return make_response(jsonify({"error" : "Invalid id format"} ), 422)
    if request.args.get('vote') == "up":
        added_vote = {
            "trivias.$.upvotes": token["user"]
        }
        removed_vote = {
            "trivias.$.downvotes": token["user"]
        }
    elif request.args.get('vote') == "down":
        added_vote = {
            "trivias.$.downvotes": token["user"]
        }
        removed_vote = {
            "trivias.$.upvotes": token["user"]
        }
    else:
        return make_response(jsonify({"error": "Vote direction not provided"}), 404)
    try:
        episodes.update_one({"trivias._id": ObjectId(tid)}, {"$addToSet": added_vote})
        episodes.update_one({"trivias._id": ObjectId(tid)}, {"$pull": removed_vote})
    except pymongo.errors.ServerSelectionTimeoutError:
        return make_response(jsonify({"error": "Connection to database timed out"}), 500)
    except:
        return make_response(jsonify({"error": "An unknown error occurred in the database"}), 500)
    return make_response( jsonify( { "message" : "Vote recorded" } ), 200 )


@trivias_bp.route("/api/v1.0/episodes/<eid>/trivias/<tid>", methods=["DELETE"])
@jwt_required
@admin_required
def delete_trivia(token, eid, tid):
    if not all(c in string.hexdigits for c in eid):
        return make_response(jsonify({"error" : "Invalid episode id format"} ), 422)
    if not all(c in string.hexdigits for c in tid):
        return make_response(jsonify({"error" : "Invalid trivia id format"} ), 422)
    try:
        episodes.update_one( { "_id" : ObjectId(eid) }, { "$pull" : { "trivias" : \
        { "_id" : ObjectId(tid) } } } )
    except pymongo.errors.ServerSelectionTimeoutError:
        return make_response(jsonify({"error": "Connection to database timed out"}), 500)
    except:
        return make_response(jsonify({"error": "An unknown error occurred in the database"}), 500)
    return make_response( jsonify( {} ), 204)