﻿# mapped-willow-mapping


## Setting Up the Environment

### .NET for Testing
1. **Install .NET**: Download and install from the [.NET official website](https://dotnet.microsoft.com/download).

### Pre-Commit Hooks
1. **Install Pre-Commit**: Pre-commit is now managed by Poetry. It will be installed automatically when you run `poetry install`.
2. **Activate Hooks**: Run `pre-commit install` in your repository to activate the git hooks.

### Python and Poetry
1. **Install Python**: Download and install Python from the [Python official website](https://python.org).
2. **Install Poetry**: Follow the instructions on the [Poetry website](https://python-poetry.org/docs/).
3. **Install Dependencies**: Inside your project directory, run `poetry install` to install all required Python dependencies in a virtual environment managed by Poetry.
4. **Activate Poetry Virtual Environment**: Execute `poetry shell` in the project directory to start the virtual environment.

## Contributing

### Adding to Manual Mapping Files
- Add your manual mappings to the `./data` directory, which is the central location for all manual mapping files.

### Local Testing

1. **Generate Inferred Mappings**:
   - Before running the tests, it's important to generate the inferred mappings. This can be done by executing the following Python script:
     ```
     poetry run python ./scripts/generate_mappings.py
     ```
   - This script will create the inferred mappings and place them in the appropriate directory.

2. **Build the Project**:
   - Once the inferred mappings are generated, the next step is to build the dotnet project. This prepares the project for running tests. Use the command:
     ```
     dotnet build
     ```

3. **Run the Tests**:
   - After building the project, run the tests to check the integrity and functionality of your code. Execute:
     ```
     dotnet test Ontologies.Mappings/test/Ontologies.Mappings.Test.csproj
     ```

By following these steps, you can perform local testing, ensuring that both the inferred mappings work correctly.

### Pre-Commit Hook Preparation
- Before committing your code, ensure you have set up pre-commit hooks as described in the environment setup section.
- The pre-commit hooks will automatically:
  - Sort the manual mapping files in `data/Mapped2Willow.json` and `data/Willow2Mapped.json`
  - Format JSON files (excluding the manual mapping files)
- If pre-commit modifies any files, you'll need to stage those changes and commit again.

## Additional Resources
- [.NET Documentation](https://docs.microsoft.com/en-us/dotnet/)
- [Python Documentation](https://docs.python.org/3/)
- [Poetry Documentation](https://python-poetry.org/docs/)

