from app import create_app

# Запуск приложения
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
