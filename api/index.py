from flask import Flask, request, jsonify, Response
import requests
import ast
import operator

app = Flask(__name__)

OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

def eval(expr):
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


# Airport temperature
def get_airport_temp(iata_code):
    """Get current temperature at an airport using wttr.in."""
    url = f"https://wttr.in/{iata_code}?format=%t"
    resp = requests.get(url, headers={"User-Agent": "curl/7.68.0"}, timeout=10)
    resp.raise_for_status()
    # Response is like "+12°C" or "-3°C"
    temp_str = resp.text.strip().replace("°C", "").replace("+", "")
    return float(temp_str)


# Stock price
def get_stock_price(symbol):
    """Get current stock price using yfinance."""
    import yfinance as yf
    ticker = yf.Ticker(symbol)
    data = ticker.history(period="1d")
    if data.empty:
        raise ValueError(f"No data found for symbol: {symbol}")
    return float(data['Close'].iloc[-1])


# Main route
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
            result = eval(eval_expr)
        else:
            result = None
    except Exception as e:
        result = None

    # Determine response format based on Accept header
    if 'application/xml' in accept or 'text/xml' in accept:
        xml_value = result if result is not None else ""
        content_type = 'application/xml'
        if 'text/xml' in accept:
            content_type = 'text/xml'
        xml_response = f'<?xml version="1.0" encoding="UTF-8"?>\n<result>{xml_value}</result>'
        return Response(xml_response, content_type=content_type)
    else:
        return jsonify(result)