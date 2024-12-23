import math
import re
import pymongo.errors
from flask import Blueprint, request, make_response, jsonify
import string
from bson import ObjectId
from decorators import jwt_required, admin_required
import globals

episodes_bp = Blueprint("episodes_bp", __name__)

episodes = globals.db.episodes

@episodes_bp.route("/api/v1.0/episodes", methods=["GET"])
def show_all_episodes():
    query = {}
    page_num, page_size = 1, 10
    if request.args.get('title'):
        query = { "title" : {"$regex" : re.compile(str(request.args.get('title')), re.IGNORECASE) } }
    if request.args.get('pn'):
        page_num = int(request.args.get('pn'))
    if request.args.get('ps'):
        page_size = int(request.args.get('ps'))
    page_start = (page_size * (page_num - 1))
    data_to_return = []
    try:
        for episode in episodes.find(query).skip(page_start).limit(page_size):
            episode['_id'] = str(episode['_id'])
            for trivia in episode['trivias']:
                trivia['_id'] = str(trivia['_id'])
            data_to_return.append(episode)
    except pymongo.errors.ServerSelectionTimeoutError:
        return make_response(jsonify({"error" : "Connection to database timed out"} ), 500)
    except:
        return make_response(jsonify({"error" : "An unknown error occurred in the database"}), 500)
    if request.args.get('title'):
        total_pages = 1
        page_num = 1
    else:
        total_pages = 62 / page_size
    return make_response( jsonify({"this_page" : page_num, "total_pages" : math.ceil(total_pages),
                                   "data": data_to_return}), 200 )

@episodes_bp.route("/api/v1.0/episodes/<string:id>", methods=["GET"])
def show_one_episode(id):
    if not all(c in string.hexdigits for c in id):
        return make_response(jsonify({"error" : "Invalid id format"} ), 422)
    try:
        episode = episodes.find_one({'_id': ObjectId(id)})
    except pymongo.errors.ServerSelectionTimeoutError:
        return make_response(jsonify({"error" : "Connection to database timed out"} ), 500)
    except:
        return make_response(jsonify({"error" : "An unknown error occurred in the database"}), 500)
    if episode is not None:
        episode['_id'] = str(episode['_id'])
        for trivia in episode['trivias']:
            trivia['_id'] = str(trivia['_id'])
        return make_response( jsonify( episode ), 200 )
    else:
        return make_response( jsonify({"error" : "Invalid episode ID"} ), 404 )

@episodes_bp.route("/api/v1.0/episodes/<string:id>", methods=["PATCH"])
@jwt_required
@admin_required
def edit_episode(token, id):
    if not all(c in string.hexdigits for c in id):
        return make_response(jsonify({"error" : "Invalid id format"} ), 422)
    if "imdbRating" in request.form:
        try:
            result = episodes.update_one({ "_id" : ObjectId(id) }, {
                "$set" : {
                    "imdbRating" : int(request.form["imdbRating"]),
                }
            })
        except pymongo.errors.ServerSelectionTimeoutError:
            return make_response(jsonify({"error": "Connection to database timed out"}), 500)
        except ValueError:
            return make_response(jsonify({"error": "Invalid imdbRating input"}), 422)
        except:
            return make_response(jsonify({"error": "An unknown error occurred in the database"}), 500)
        if result.matched_count == 1:
            edited_episode_link = "http://localhost:5000/api/v1.0/episodes/" + id
            return make_response( jsonify({ "url":edited_episode_link } ), 200)
        else:
            return make_response( jsonify({ "error":"Invalid episode ID" } ), 404)
    else:
        return make_response( jsonify({ "error" : "Missing form data" } ), 404)