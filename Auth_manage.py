import pandas as pd
import streamlit as st

MASTER_CODE = st.secrets["MASTER_CODE"]

BLANK_CODE_VALUES = {"", "none", "nan", "empty"}
DEFAULT_QUOTA = 5


def normalize_code(value):
    """
    Normalize access code values from user input or spreadsheet data.
    Handles NaN, None, empty strings, and numeric-like strings ending with '.0'.
    """
    if value is None or pd.isna(value):
        return ""

    code = str(value).strip()

    # Prevent spreadsheet numeric formatting issues
    if code.endswith(".0"):
        code = code[:-2]

    return code


def is_blank_code(value):
    """
    Return True if the access code should be treated as blank/guest access.
    """
    code = normalize_code(value).lower()
    return code in BLANK_CODE_VALUES


def count_registered_by_code(df, code):
    """
    Count entries registered with a specific access code.
    Blank/guest entries are counted robustly.
    """
    if df is None or df.empty or "access_code" not in df.columns:
        return 0

    access_codes = df["access_code"].apply(normalize_code)

    # Guest entries
    if is_blank_code(code):
        return access_codes.str.lower().isin(BLANK_CODE_VALUES).sum()

    # Authorized access code entries
    return (access_codes == normalize_code(code)).sum()


def check_registration_quota(df, input_code, auth_df):
    """
    Check whether a new registration is allowed under the given access code.

    Rules:
    - Master code: unlimited registration.
    - Blank code: guest registration, limited to 5 entries.
    - Authorized user code: quota is read from auth_df.
    - Invalid code: registration denied.
    """

    code = normalize_code(input_code)

    # ==========================================
    # Master Access
    # ==========================================
    if code == MASTER_CODE:
        return True, "Master access granted. Unlimited quota enabled."

    # ==========================================
    # Guest Access
    # ==========================================
    if is_blank_code(code):
        current_count = count_registered_by_code(df, code)
        quota_limit = 5

        if current_count >= quota_limit:
            return False, (
                "⚠️ Guest quota exceeded (Limit: 5). "
                "Please use an authorized Access Code."
            )

        next_count = current_count + 1

        return True, (
            f"Guest access granted. "
            f"Usage: {next_count}/{quota_limit}."
        )

    # ==========================================
    # Authorized Access Codes
    # ==========================================
    if auth_df is not None and not auth_df.empty and "Code" in auth_df.columns:

        auth_codes = auth_df["Code"].apply(normalize_code)

        # Registered access code only
        if code in auth_codes.values:

            try:
                quota_limit = int(
                    auth_df.loc[auth_codes == code, "Quota"].iloc[0]
                )

            except (ValueError, TypeError, IndexError, KeyError):

                # Restrict registration using fallback quota
                current_count = count_registered_by_code(df, code)

                if current_count >= DEFAULT_QUOTA:
                    return False, (
                        f"⚠️ Temporary quota exceeded for code [{code}] "
                        f"(Limit: {DEFAULT_QUOTA}). "
                        f"Please contact the administrator."
                    )

                next_count = current_count + 1

                return True, (
                    f"⚠️ Quota configuration issue detected for code [{code}]. "
                    f"Temporary limit applied "
                    f"(Usage: {next_count}/{DEFAULT_QUOTA}). "
                    f"Please contact the administrator."
                )

            current_count = count_registered_by_code(df, code)

            if current_count >= quota_limit:
                return False, (
                    f"⚠️ Limit reached for code [{code}]. "
                    f"(Usage: {current_count}/{quota_limit})"
                )

            next_count = current_count + 1

            return True, (
                f"Authorized access granted. "
                f"Usage: {next_count}/{quota_limit}."
            )

    # ==========================================
    # Invalid Access Code
    # ==========================================
    return False, "❌ Invalid Access Code. Please contact the administrator."


def is_authorized(input_code, stored_code):
    """
    Check whether the input access code is authorized
    for an existing record.

    Rules:
    - Master code always grants access.
    - Records with blank/guest access codes are editable by any user.
    - Otherwise, the input code must match the stored code.
    """

    input_code = normalize_code(input_code)
    stored_code = normalize_code(stored_code)

    # Master override
    if input_code == MASTER_CODE:
        return True

    # Guest-access records
    if is_blank_code(stored_code):
        return True

    # Normal authorization
    return input_code == stored_code


def is_edit_authorized(input_code, stored_code):
    """
    Alias for edit/delete authorization.
    Use this in UI pages when opening editors or deleting records.
    """
    return is_authorized(input_code, stored_code)