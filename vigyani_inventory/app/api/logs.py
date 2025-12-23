from flask import Blueprint, request, jsonify
from ..models.logs import Logs
import json
import logging

logger = logging.getLogger(__name__)
logs_bp = Blueprint('logs', __name__)

@logs_bp.route('/logs', methods=['GET'])
def get_all_logs():
    try:
        status = request.args.get('status')

        if not status:
            logs = Logs.get_all_logs()
        elif status :
            logs = Logs.get_log_by_status(status)
        else:
            return jsonify({'message': 'Invalid request'}), 400

        if not logs:
            return jsonify({'message': 'Log not found'}), 404
        
        log_list = [{
            'id': log.id,
            'txnid': log.txnid,
            'status': log.status,
            'amount': log.amount,
            'created_at': log.created_at.isoformat(),
        } for log in logs]
            
        return jsonify({'logs': log_list}), 200

    except Exception as e:
        logger.error(f"Error fetching logs: {str(e)}")
        return jsonify({'error': 'Failed to fetch log'}), 500
    
@logs_bp.route('/logs/id', methods=['GET'])
def get_log_by_txnid():
    try:
        txnid = request.args.get('txn_id')
        log = Logs.get_log_by_txnid(txnid)

        if not log:
            return jsonify({'message': 'Log not found'}), 404
        
        user_log = {
            'id': log.id,
            'txnid': log.txnid,
            'status': log.status,
            'amount': log.amount,
            'created_at': log.created_at.isoformat(),
        }
        return jsonify({'log': user_log}), 200
    
    except Exception as e:
        logger.error(f"Error fetching log by id: {str(e)}")
        return jsonify({'error': 'Failed to fetch log'}), 500
