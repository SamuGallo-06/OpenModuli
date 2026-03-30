from flask import Blueprint, jsonify

server_bp = Blueprint('server', __name__, url_prefix='/server')

@server_bp.route("/status")
def status():
    return jsonify({"status": "ok"})

@server_bp.route("/restart")
def restart():
    # logica di restart
    return jsonify({"message": "restarting"})

@server_bp.route("/shudown")
def shutdown():
    # logica di restart
    return jsonify({"message": "[SERVER] Shutting Down System"})