"""Create an empty Excel review template without network access."""
from pathlib import Path
from .excel_export import export_excel
if __name__ == '__main__':
    path=export_excel([],[],Path('output/TrialWatch_Case_Review.xlsx'))
    print(path)
