import pandas as pd


def extract_excel_data(
    excel_path: str,
    sheet_name=0,
    start_row: int = 9,
    step: int = 6
) -> pd.DataFrame:
    """
    Extract Hardness (G), Type (J), and Material (V)
    starting at start_row and taking every `step` rows.
    """

    df = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)

    col_indices = {
        "Hardness": 6,   # G
        "Type": 9,       # J
        "Material": 21   # V
    }

    start_index = start_row - 1
    selected_rows = df.iloc[start_index::step]

    extracted = selected_rows.iloc[:, list(col_indices.values())]
    extracted.columns = col_indices.keys()

    return extracted.reset_index(drop=True)


def create_combined_csv(
    csv_path: str,
    excel_path: str,
    output_path: str,
    failed_indices: list,
    sheet_name=0
) -> None:
    """
    Creates a new CSV file combining:
    - X_aligned, Y_aligned, Z_aligned from CSV
    - Hardness, Type, Material from Excel

    Writes result to output_path.
    """

    csv_df = pd.read_csv(csv_path)

    required_cols = {"X_aligned", "Y_aligned", "Z_aligned"}
    if not required_cols.issubset(csv_df.columns):
        raise ValueError(
            f"CSV must contain columns: {required_cols}"
        )

    csv_df = csv_df.reset_index(drop=True)

    # Filter out failed indices from CSV only
    if failed_indices:
        csv_df = csv_df.drop(index=failed_indices, errors='ignore').reset_index(drop=True)

    excel_df = extract_excel_data(excel_path, sheet_name=sheet_name)

    min_len = min(len(csv_df), len(excel_df))

    combined_df = pd.concat(
        [csv_df.iloc[:min_len], excel_df.iloc[:min_len]],
        axis=1
    )

    combined_df.to_csv(output_path, index=False)