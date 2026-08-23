import json
import os
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from services import pantry_service, settings_service, llm_service

app = Flask(__name__)

# Ensure data and config files exist at startup
pantry_service.ensure_pantry_file_exists()
settings_service.ensure_config_exists()


# -------------------------------------------------------------
# Web Page Routes
# -------------------------------------------------------------

@app.route('/')
@app.route('/cooking')
def cooking_page():
    return render_template('cooking.html', active_page='cooking')


@app.route('/pantry')
def pantry_page():
    return render_template('pantry.html', active_page='pantry')


@app.route('/customization')
def customization_page():
    return render_template('customization.html', active_page='customization')


# -------------------------------------------------------------
# Pantry API
# -------------------------------------------------------------

@app.route('/api/pantry', methods=['GET'])
def get_pantry():
    try:
        items = pantry_service.get_all_items()
        return jsonify({'success': True, 'items': items})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/pantry', methods=['POST'])
def add_pantry_item():
    try:
        data = request.get_json() or {}
        item = data.get('item')
        quantity = data.get('quantity', 1)
        units = data.get('units', '')
        date_added = data.get('date_added')

        if not item:
            return jsonify({'success': False, 'error': 'Item name is required.'}), 400

        result = pantry_service.add_item(item, quantity, units, date_added)
        return jsonify({'success': True, 'item': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/pantry/batch', methods=['POST'])
def add_pantry_batch():
    try:
        data = request.get_json() or {}
        items = data.get('items', [])
        if not isinstance(items, list):
            return jsonify({'success': False, 'error': 'Items must be a list.'}), 400

        updated = pantry_service.add_items(items)
        return jsonify({'success': True, 'items': updated})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/pantry', methods=['DELETE'])
def remove_pantry_items():
    try:
        data = request.get_json() or {}
        item_names = data.get('items', [])
        if isinstance(item_names, str):
            item_names = [item_names]

        updated = pantry_service.remove_items(item_names)
        return jsonify({'success': True, 'items': updated})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/pantry/import', methods=['POST'])
def import_pantry_csv():
    try:
        data = request.get_json() or {}
        filename = data.get('filename', 'pantry_import.csv')
        result = pantry_service.import_csv(filename)
        return jsonify({'success': True, 'result': result})
    except FileNotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/pantry/clear', methods=['POST'])
def clear_pantry():
    try:
        pantry_service.clear_pantry()
        return jsonify({'success': True, 'message': 'Pantry cleared successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# -------------------------------------------------------------
# Settings API
# -------------------------------------------------------------

@app.route('/api/settings', methods=['GET'])
def get_settings():
    try:
        settings = settings_service.get_settings()
        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/settings', methods=['POST'])
def save_settings():
    try:
        data = request.get_json() or {}
        updated = settings_service.save_settings(data)
        return jsonify({'success': True, 'settings': updated})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


# -------------------------------------------------------------
# SLM (Recipe & Shopping) API
# -------------------------------------------------------------
#
# These stream Server-Sent-Events style frames (`data: {...}\n\n`) instead of a
# single JSON blob. That's what gives the frontend live visibility into what
# Ollama is doing (tokens as they arrive, heartbeats, stall warnings) rather
# than a silent multi-minute wait followed by one big response or nothing.

def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


def _sse_response(event_generator):
    def wrapped():
        try:
            for event in event_generator:
                yield _sse(event)
        except Exception as e:
            # Catch-all so a bug in the generator surfaces as a visible error
            # event instead of silently truncating the stream.
            yield _sse({'type': 'error', 'message': str(e)})

    return Response(
        stream_with_context(wrapped()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',  # disable proxy buffering, if any sits in front
        },
    )


@app.route('/api/recipe', methods=['POST'])
def generate_recipe():
    data = request.get_json() or {}
    prompt = data.get('prompt', '').strip()
    if not prompt:
        return jsonify({'success': False, 'error': 'Please provide a dish or recipe prompt.'}), 400

    return _sse_response(llm_service.stream_recipe(prompt))


@app.route('/api/shopping', methods=['POST'])
def generate_shopping_list():
    data = request.get_json() or {}
    prompt = data.get('prompt', '').strip()

    return _sse_response(llm_service.stream_shopping_list(prompt if prompt else None))


if __name__ == '__main__':
    print("Starting LocalChef server on http://localhost:5000")
    # threaded=True matters here: a recipe/shopping-list request now holds its
    # connection open for the whole generation (potentially minutes on CPU-only
    # Ollama). Without threading, the single-worker dev server would block all
    # other requests (including the Stop button's abort and other pages) until
    # that one finishes.
    app.run(host='127.0.0.1', port=5000, debug=True, threaded=True)
