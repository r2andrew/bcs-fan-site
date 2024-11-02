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
    stages = [ { "$match" : {"_id" : ObjectId(id)} },
        {
            "$addFields": {
                "trivias": {
                    "$map": {
                        "input": "$trivias",
                        "as": "item",
                        "in": {
                            "$mergeObjects": [
                                "$$item",
                                {
                                    "score": {"$subtract" : [
                                        { "$cond": { "if": { "$isArray": "$$item.upvotes" },
                                                     "then": { "$size": "$$item.upvotes" }, "else": 0}},
                                        { "$cond": { "if": { "$isArray": "$$item.downvotes" },
                                                     "then": { "$size": "$$item.downvotes" }, "else": 0}}
                                    ] }
                                }
                            ]
                        }
                    }
                }
            }
        }
    ]
    data_to_return = []
    try:
        episode = list(episodes.aggregate(stages))
    except pymongo.errors.ServerSelectionTimeoutError:
        return make_response(jsonify({"error": "Connection to database timed out"}), 500)
    except:
        return make_response(jsonify({"error": "An unknown error occurred in the database"}), 500)
    for trivia in episode[0]["trivias"]:
        trivia["_id"] = str(trivia["_id"])
        data_to_return.append(trivia)
    return make_response( jsonify( data_to_return ), 200 )

@trivias_bp.route("/api/v1.0/episodes/<eid>/trivias/<tid>", methods=["GET"])
def fetch_one_trivia(eid, tid):
    if not all(c in string.hexdigits for c in eid):
        return make_response(jsonify({"error" : "Invalid episode id format"} ), 422)
    if not all(c in string.hexdigits for c in tid):
        return make_response(jsonify({"error" : "Invalid trivia id format"} ), 422)
    stages = [{"$match": {"_id": ObjectId(eid)}},
                {"$unwind" : "$trivias"},
                {"$match" : {"trivias._id": ObjectId(tid)}},
                {"$project" : {"trivias" : 1, "_id" : 0}},
                {"$addFields" : {
                    "trivias.score": {"$subtract": [
                        {"$cond": {"if": {"$isArray": "$trivias.upvotes"},
                                 "then": {"$size": "$trivias.upvotes"}, "else": 0}},
                        {"$cond": {"if": {"$isArray": "$trivias.downvotes"},
                                 "then": {"$size": "$trivias.downvotes"}, "else": 0}}
                        ]}
                    }
                }
            ]
    try:
        episode = list(episodes.aggregate(stages))
    except pymongo.errors.ServerSelectionTimeoutError:
        return make_response(jsonify({"error": "Connection to database timed out"}), 500)
    except:
        return make_response(jsonify({"error": "An unknown error occurred in the database"}), 500)
    if not episode:
        return make_response(jsonify({"error":"Invalid episode ID or trivia ID"}),404)
    episode[0]["trivias"]['_id'] = str(episode[0]['trivias']['_id'])
    return make_response( jsonify(episode[0]['trivias']), 200)

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

@trivias_bp.route("/api/v1.0/episodes/<string:eid>/trivias/<tid>/vote", methods=["PATCH"])
@jwt_required
def vote_on_trivia(token, eid, tid):
    if not all(c in string.hexdigits for c in tid):
        return make_response(jsonify({"error" : "Invalid id format"} ), 422)
    if request.args.get('vote') == "up":
        added_vote = { "trivias.$.upvotes": token["user"] }
        removed_vote = { "trivias.$.downvotes": token["user"] }
    elif request.args.get('vote') == "down":
        added_vote = { "trivias.$.downvotes": token["user"] }
        removed_vote = { "trivias.$.upvotes": token["user"] }
    else:
        return make_response(jsonify({"error": "Vote direction not provided"}), 422)
    try:
        episodes.update_one({"trivias._id": ObjectId(tid)}, {"$addToSet": added_vote})
        episodes.update_one({"trivias._id": ObjectId(tid)}, {"$pull": removed_vote})
    except pymongo.errors.ServerSelectionTimeoutError:
        return make_response(jsonify({"error": "Connection to database timed out"}), 500)
    except:
        return make_response(jsonify({"error": "An unknown error occurred in the database"}), 500)
    edited_trivia_url = "http://localhost:5000/api/v1.0/episodes/" + \
        eid + "/trivias/" + tid
    return make_response( jsonify( { "url" : edited_trivia_url } ), 200 )

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