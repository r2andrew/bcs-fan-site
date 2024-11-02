from flask import Flask
from blueprints.episodes.episodes import episodes_bp
from blueprints.trivia.trivia import trivias_bp
from blueprints.users.users import users_bp
from blueprints.auth.auth import auth_bp
app = Flask(__name__)
app.register_blueprint(episodes_bp)
app.register_blueprint(trivias_bp)

app.register_blueprint(users_bp)
app.register_blueprint(auth_bp)


if __name__ == "__main__":
    app.run(debug=True)