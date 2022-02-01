from setuptools import setup

if __name__ == '__main__':
    setup(
        entry_points={
            'flake8.extension': [
                'F82 = flake_rba:ReferencedBeforeAssignmentASTPlugin'
            ],
        }
    )
