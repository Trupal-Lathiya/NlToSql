import os

# Define folder structure
structure = {
    "frontend": {
        "public": ["index.html"],
        "src": {
            "services": ["apiClient.js"],
            "hooks": ["useHistory.js"],
            "components": [
                "Sidebar.jsx",
                "Sidebar.css",
                "SqlDisplay.jsx",
                "ResultsTable.jsx"
            ],
            "pages": [
                "ChatPage.jsx",
                "HistoryPage.jsx",
                "QueryPage.jsx"
            ],
            "": ["App.jsx", "index.js", "index.css"]
        },
        "": ["package.json", ".env.example"]
    }
}

def create_structure(base_path, structure):
    for folder, contents in structure.items():
        current_path = os.path.join(base_path, folder) if folder else base_path
        
        if folder:
            os.makedirs(current_path, exist_ok=True)

        if isinstance(contents, dict):
            create_structure(current_path, contents)
        elif isinstance(contents, list):
            for file in contents:
                file_path = os.path.join(current_path, file)
                with open(file_path, "w") as f:
                    pass  # create empty file

# Run script
create_structure(".", structure)

print("Frontend structure created successfully!")