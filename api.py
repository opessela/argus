from flask import Flask, request, render_template
from flask_restful import Resource, Api
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.json_util import dumps

mongo = MongoClient("mongo")


app = Flask(__name__)
api = Api(app)


class HelloWorld(Resource):
    def get(self):
        return {'hello': 'world'}


class Events(Resource):

    def get(self, id=None):
        if id:
            pass
        else:
            cursor = mongo.db.events.find({}, {"_id": 0})
            logs = [a for a in cursor]
            return logs

    def post(self, id=None):
        # endpoint to start job
        if id:
            pass
        # new event received via api
        else:
            if request.json:
                print request.json
                object_id = ObjectId()
                data = {"id": str(object_id),
                        "action": request.json['action'],
                        "vlan": request.json['vlan'],
                        "node": request.json['node'],
                        "port": request.json['port'],
                        "ucsm": request.json['ucsm']
                        }

                mongo.db.events.insert(data)
                event = mongo.db.events.find_one({"id": object_id})

                return dumps(event)


    def delete(self, id=None):
        try:
            event = mongo.db.events.find_one({"id": id})
            print "deleting event {}".format(event)
            mongo.db.events.delete_one({'id': id})
            return {'status': 'deleted'}, 200
        except AttributeError:
            return {"status": "not found"}, 404


@app.route('/')
def index():
    return render_template('index.html')
api.add_resource(HelloWorld, '/')
api.add_resource(Events, '/api/events', '/api/events/<string:id>')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
