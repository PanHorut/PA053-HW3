from flask import Flask, request, jsonify, Response
import requests
import ast
import operator

app = Flask(__name__)


# --- Safe arithmetic expression evaluator ---
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

def safe_eval(expr):
    """Safely evaluate an arithmetic expression containing integers, +, -, *, /, parentheses."""
    tree = ast.parse(expr, mode='eval')
    return _eval_node(tree.body)

def _eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    elif isinstance(node, ast.BinOp):
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        op = OPERATORS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return op(left, right)
    elif isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand)
        op = OPERATORS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
        return op(operand)
    else:
        raise ValueError(f"Unsupported expression node: {type(node).__name__}")


# --- Airport temperature via wttr.in ---
def get_airport_temp(iata_code):
    """Get current temperature at an airport using wttr.in JSON API."""
    url = f"https://wttr.in/{iata_code}?format=j1"
    resp = requests.get(url, headers={"User-Agent": "curl/7.68.0"}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    temp_c = data['current_condition'][0]['temp_C']
    return float(temp_c)


# --- Stock price via yfinance ---
def get_stock_price(symbol):
    """Get current stock price using yfinance."""
    import yfinance as yf
    ticker = yf.Ticker(symbol)
    data = ticker.history(period="1d")
    if data.empty:
        raise ValueError(f"No data found for symbol: {symbol}")
    return float(data['Close'].iloc[-1])


# --- Main route ---
@app.route('/')
def home():
    airport = request.args.get('queryAirportTemp')
    stock = request.args.get('queryStockPrice')
    eval_expr = request.args.get('queryEval')

    accept = request.headers.get('Accept', '')

    result = None

    try:
        if airport:
            result = get_airport_temp(airport)
        elif stock:
            result = get_stock_price(stock)
        elif eval_expr:
            # In query strings, + is decoded as space, so convert back
            eval_expr = eval_expr.replace(' ', '+')
            result = safe_eval(eval_expr)
        else:
            result = None
    except Exception as e:
        result = None

    # Determine response format based on Accept header
    # Browsers send "text/html,...,application/xml;q=0.9" by default,
    # so only return XML if client explicitly wants it (no text/html present)
    wants_xml = ('application/xml' in accept or 'text/xml' in accept) and 'text/html' not in accept

    if wants_xml:
        xml_value = result if result is not None else ""
        content_type = 'application/xml'
        if 'text/xml' in accept and 'application/xml' not in accept:
            content_type = 'text/xml'
        xml_response = f'<?xml version="1.0" encoding="UTF-8"?>\n<r>{xml_value}</r>'
        return Response(xml_response, content_type=content_type)
    else:
        return jsonify(result)