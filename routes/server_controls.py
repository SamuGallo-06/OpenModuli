from flask import Blueprint, jsonify
from utilities.server_manager import reboot_system, shutdown_system

server_bp = Blueprint('server', __name__, url_prefix='/server')

@server_bp.route("/status")
def status():
    return jsonify({"status": "ok"})

@server_bp.route("/restart")
def restart():
    reboot_system()
    return jsonify({"status": "restarting"})

@server_bp.route("/shutdown")
def shutdown():
    shutdown_system()
    return jsonify({"status": "shutting down"})