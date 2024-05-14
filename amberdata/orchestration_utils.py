import json
import logging
import os
import sys
from os import environ as env
from pathlib import Path
from time import time
from typing import Any, Dict, List, Tuple

import pandas as pd
import pygsheets
import snowflake.connector
import yaml
from snowflake.sqlalchemy import URL as snowflake_URL
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from yaml.loader import SafeLoader


def postgres_engine_factory(args: Dict[str, str]) -> Engine:
    """
    Create a database engine from a dictionary of database info.
    """

    db_address = args["PG_ADDRESS"]
    db_database = args["PG_DATABASE"]
    db_port = args["PG_PORT"]
    db_username = args["PG_USERNAME"]
    db_password = args["PG_PASSWORD"]

    conn_string = (
        f"postgresql://{db_username}:{db_password}@{db_address}:{db_port}/{db_database}"
    )

    return create_engine(conn_string, connect_args={"sslcompression": 0})


def bizible_snowflake_engine_factory(
    args: Dict[str, str], role: str, schema: str = ""
) -> Engine:
    """
    Create a database engine from a dictionary of database info.
    Separate convenience function for bizible as it would create a strange conditional in the general function.
    """
    role_dict = {
        # Note: This Bizible user is used for extracting data from Bizible
        "BIZIBLE_USER": {
            "USER": "BIZIBLE_SNOWFLAKE_USER",
            "PASSWORD": "BIZIBLE_SNOWFLAKE_PASSWORD",
            "ACCOUNT": "BIZIBLE_SNOWFLAKE_ACCOUNT",
            "DATABASE": "BIZIBLE_SNOWFLAKE_DATABASE",
            "WAREHOUSE": "BIZIBLE_SNOWFLAKE_WAREHOUSE",
            "ROLE": "BIZIBLE_SNOWFLAKE_ROLE",
        }
    }
    vars_dict = role_dict[role]

    conn_string = snowflake_URL(
        user=args[vars_dict["USER"]],
        password=args[vars_dict["PASSWORD"]],
        account=args[vars_dict["ACCOUNT"]],
        database=args[vars_dict["DATABASE"]],
        warehouse=args[vars_dict["WAREHOUSE"]],
        role=args[vars_dict["ROLE"]],
        schema=schema,
    )

    return create_engine(conn_string, connect_args={"sslcompression": 0})


def snowflake_engine_factory(
    args: Dict[str, str],
    role: str,
    schema: str = "",
    load_warehouse: str = "SNOWFLAKE_LOAD_WAREHOUSE",
) -> Engine:
    """
    Create a database engine from a dictionary of database info.
    """

    
    role_dict = {
        "SYSADMIN": {
            "USER": "SNOWFLAKE_USER",
            "PASSWORD": "SNOWFLAKE_PASSWORD",
            "ACCOUNT": "SNOWFLAKE_ACCOUNT",
            "DATABASE": "SNOWFLAKE_LOAD_DATABASE",
            "WAREHOUSE": load_warehouse,
            "ROLE": "SYSADMIN",
        },
        "ANALYTICS_LOADER": {
            "USER": "SNOWFLAKE_LOAD_USER",
            "PASSWORD": "SNOWFLAKE_LOAD_PASSWORD",
            "ACCOUNT": "SNOWFLAKE_ACCOUNT",
            "DATABASE": "SNOWFLAKE_PROD_DATABASE",
            "WAREHOUSE": load_warehouse,
            "ROLE": "LOADER",
        },
        "LOADER": {
            "USER": "SNOWFLAKE_LOAD_USER",
            "PASSWORD": "SNOWFLAKE_LOAD_PASSWORD",
            "ACCOUNT": "SNOWFLAKE_ACCOUNT",
            "DATABASE": "SNOWFLAKE_LOAD_DATABASE",
            "WAREHOUSE": load_warehouse,
            "ROLE": "LOADER",
        },
        "DATA_SCIENCE_LOADER": {
            "USER": "SNOWFLAKE_DATA_SCIENCE_LOAD_USER",
            "PASSWORD": "SNOWFLAKE_DATA_SCIENCE_LOAD_PASSWORD",
            "ACCOUNT": "SNOWFLAKE_ACCOUNT",
            "DATABASE": "SNOWFLAKE_PROD_DATABASE",
            "WAREHOUSE": load_warehouse,
            "ROLE": "DATA_SCIENCE_LOADER",
        },
        "CI_USER": {
            "USER": "SNOWFLAKE_USER",  ## this is the CI User
            "PASSWORD": "SNOWFLAKE_PASSWORD",
            "ACCOUNT": "SNOWFLAKE_ACCOUNT",
            "DATABASE": "SNOWFLAKE_PROD_DATABASE",
            "WAREHOUSE": "SNOWFLAKE_TRANSFORM_WAREHOUSE",
            "ROLE": "TRANSFORMER",
        },
        "SALES_ANALYTICS": {
            "USER": "SNOWFLAKE_LOAD_USER",
            "PASSWORD": "SNOWFLAKE_LOAD_PASSWORD",
            "ACCOUNT": "SNOWFLAKE_ACCOUNT",
            "DATABASE": "SNOWFLAKE_LOAD_DATABASE",
            "WAREHOUSE": load_warehouse,
            "ROLE": "SALES_ANALYTICS",
        },
    }

    vars_dict = role_dict[role]

    conn_string = snowflake_URL(
        user=args[vars_dict["USER"]],
        password=args[vars_dict["PASSWORD"]],
        account=args[vars_dict["ACCOUNT"]],
        database=args[vars_dict["DATABASE"]],
        warehouse=args[vars_dict["WAREHOUSE"]],
        role=vars_dict["ROLE"],  # Don't need to do a lookup on this one
        schema=schema,
    )

    return create_engine(conn_string, connect_args={"sslcompression": 0})


def get_env_from_profile(
    environment: str,
    in_docker: bool,
) -> Dict:
    """ """
    if in_docker:
        profile_location = "/usr/local/snowflake_profile/profiles.yml"
    else:
        from pathlib import Path

        home = str(Path.home())

        profile_location: str = f"{home}/.dbt/profiles.yml"

    # Open the file and load the file
    with open(profile_location) as f:
        data = yaml.load(f, Loader=SafeLoader)
        data = data.get("github-snowflake")
        return data.get("outputs").get(environment)


def data_science_engine_factory(
    args: Dict[str, str],
    profile_target: str = "dev",
    schema: str = "",
    in_docker: bool = False,
    run_target: str = "local",
):
    """
    Convenience function to extract dbt keys and return a simpler engine for use in Data Science
    """

    # Figure out which vars to grab

    if run_target == "local":
        vars_dict = get_env_from_profile(profile_target, in_docker)

        # If no password is provided; use SSO
        conn_string = snowflake.connector.connect(
            user=vars_dict.get("user"),
            authenticator="externalbrowser",
            account=vars_dict.get("account"),
            database=vars_dict.get("database"),
            warehouse=vars_dict.get("warehouse"),
            role=vars_dict.get("role"),
            schema=schema,
        )

    else:
        role_dict = {
            "DATA_SCIENCE_LOADER": {
                "USER": "SNOWFLAKE_DATA_SCIENCE_LOAD_USER",
                "PASSWORD": "SNOWFLAKE_DATA_SCIENCE_LOAD_PASSWORD",
                "ACCOUNT": "SNOWFLAKE_ACCOUNT",
                "DATABASE": "SNOWFLAKE_PROD_DATABASE",
                "WAREHOUSE": "SNOWFLAKE_LOAD_WAREHOUSE",
                "ROLE": "DATA_SCIENCE_LOADER",
            },
        }

        vars_dict = role_dict[profile_target]

        conn_string = snowflake.connector.connect(
            user=args[vars_dict["USER"]],
            password=args[vars_dict["PASSWORD"]],
            account=args[vars_dict["ACCOUNT"]],
            database=args[vars_dict["DATABASE"]],
            warehouse=args[vars_dict["WAREHOUSE"]],
            role=vars_dict["ROLE"],  # Don't need to do a lookup on this one
            schema=schema,
        )

    return conn_string


def query_executor(engine: Engine, query: str) -> List[Tuple[Any]]:
    """
    Execute DB queries safely.
    """

    try:
        connection = engine.connect()
        results = connection.execute(query).fetchall()
    finally:
        connection.close()
        engine.dispose()
    return results


def query_dataframe(engine: Engine, query: str) -> pd.DataFrame:
    """
    Convenience function to return query as DF for data science operations,
    Needed to be a separate function due to static typing of return types.
    Adds column names to results
    """
    results = query_executor(engine, query)
    if len(results) > 0:
        column_names = results[0].keys()
        return pd.DataFrame(results, columns=column_names)
    else:
        return pd.DataFrame()


def ds_query_dataframe(engine, query: str) -> pd.DataFrame:
    connection = engine.cursor()
    results = connection.execute(query).fetch_pandas_all()

    return results


def dataframe_enricher(
    advanced_metadata: bool, raw_df: pd.DataFrame, add_uploaded_at: bool = True
) -> pd.DataFrame:
    """
    Enrich a dataframe with metadata and do some cleaning.
    """
    if add_uploaded_at:
        raw_df["_uploaded_at"] = time()  # Add an uploaded_at column

    if advanced_metadata:
        # Add additional metadata from an Airflow scheduler
        # _task_instance is expected to be the task_instance_key_str
        raw_df.loc[:, "_task_instance"] = os.environ["TASK_INSTANCE"]

    # Do some Snowflake-specific sanitation
    enriched_df = (
        raw_df.applymap(  # convert dicts and lists to str to avoid snowflake errors
            lambda x: x if not isinstance(x, (list, dict)) else str(x)
        )
        .applymap(  # shorten strings that are too long
            lambda x: x[:4_194_304] if isinstance(x, str) else x
        )
        .applymap(  # replace tabs with 4 spaces
            lambda x: x.replace("\t", "    ") if isinstance(x, str) else x
        )
    )

    return enriched_df


def dataframe_uploader(
    dataframe: pd.DataFrame,
    engine: Engine,
    table_name: str,
    schema: str = None,
    advanced_metadata: bool = False,
    if_exists: str = "append",
    add_uploaded_at: bool = True,
) -> None:
    """
    Upload a dataframe, adding in some metadata and cleaning up along the way.
    """

    dataframe_enricher(advanced_metadata, dataframe, add_uploaded_at).to_sql(
        name=table_name,
        con=engine,
        schema=schema,
        index=False,
        if_exists=if_exists,
        chunksize=10000,
    )


def snowflake_stage_load_copy_remove(
    file: str,
    stage: str,
    table_path: str,
    engine: Engine,
    type: str = "json",
    on_error: str = "abort_statement",
    file_format_options: str = "",
) -> None:
    """
    This function performs remove+upload+copy+remove:
    - Remove file from Snowflake internal stage if it currently exists from prev process.
    - Upload/put file to internal stage
    - Copy file from internal stage to target table
    - Finally, remove file from internal stage
    """

    file_name = os.path.basename(file)
    if file_name.endswith(".gz"):
        full_stage_file_path = f"{stage}/{file_name}"
    else:
        full_stage_file_path = f"{stage}/{file_name}.gz"
    remove_query = f"remove @{full_stage_file_path}"
    put_query = f"put 'file://{file}' @{stage} auto_compress=true;"

    if type == "json":
        copy_query = f"""copy into {table_path} (jsontext)
                         from @{full_stage_file_path}
                         file_format=(type='{type}'),
                         on_error='{on_error}';
                         """

    else:
        copy_query = f"""copy into {table_path}
                         from @{full_stage_file_path}
                         file_format=(type='{type}' {file_format_options}),
                         on_error='{on_error}';
                        """

    logging.basicConfig(stream=sys.stdout, level=20)

    try:
        connection = engine.connect()

        logging.info(
            f"Removing file from internal stage with full_stage_file_path: {full_stage_file_path}"
        )
        connection.execute(remove_query)
        logging.info("Query successfully run")

        logging.info("Writing to Snowflake.")
        connection.execute(put_query)
        logging.info("Query successfully run")
    finally:
        connection.close()
        engine.dispose()

    try:
        connection = engine.connect()

        logging.info(f"Copying to Table {table_path}.")
        connection.execute(copy_query)
        logging.info("Query successfully run")

        logging.info(f"Removing {file} from stage.")
        connection.execute(remove_query)
        logging.info("Query successfully run")
    finally:
        connection.close()
        engine.dispose()


def push_to_xcom_file(xcom_json: Dict[Any, Any]) -> None:
    """
    Writes the json passed in as a parameter to the file path required by KubernetesPodOperator to make the json an xcom in Prefect.
    Overwrites any data already there.
    This is primarily used to push metrics to prometheus right now.
    """

    xcom_file_name = "/prefect/xcom/return.json"
    Path("/prefect/xcom/").mkdir(parents=True, exist_ok=True)
    with open(xcom_file_name, "w") as xcom_file:
        json.dump(xcom_json, xcom_file)


def append_to_xcom_file(xcom_json: Dict[Any, Any]) -> None:
    """
    Combines the parameter dictionary with any XComs that have already been written by the KubernetesPodOperator.
    This function is useful because the XComs can be written at any time during the Task run and not be written over.
    """

    existing_json = {}
    try:
        with open("/prefect/xcom/return.json") as json_file:
            existing_json = json.load(json_file)
    except IOError:
        pass  # the file doesn't exist
    except json.JSONDecodeError:
        pass  # the file is likely empty
    push_to_xcom_file({**existing_json, **xcom_json})


def write_to_gsheets(
    spreadsheet_id: str,
    sheet_name: str,
    data_df: pd.DataFrame,
    service_account_credentials: str = "GSHEETS_SERVICE_ACCOUNT_CREDENTIALS",
) -> None:
    """
    Gets a dataframe as a parameter and writes it under spreadsheet_id
    and sheet_name using a Google Service Account stored under service_file_path.
    Locally you should run it with your own Google credentials.
    The Google Sheet must be shared with the account used to write into it.
    """
    gsheets = pygsheets.authorize(service_account_env_var=service_account_credentials)
    sheet = gsheets.open_by_key(spreadsheet_id)

    logging.basicConfig(stream=sys.stdout, level=20)

    try:
        logging.info(f"Trying to create a sheet called {sheet_name}...")
        sheet.add_worksheet(sheet_name)
        logging.info("New tab created.")

    except Exception as exc:
        # A sheet with that name might already exist
        logging.error(exc)

    try:
        wks_write = sheet.worksheet_by_title(sheet_name)
        wks_write.clear("A1", None, "*")
        wks_write.set_dataframe(data_df, (1, 1), encoding="utf-8", fit=True)
        wks_write.frozen_rows = 1

    except Exception as exc:
        logging.error(exc)
        logging.error("GSheet could not be written.")


def read_from_gsheets(
    spreadsheet_id: str,
    sheet_name: str,
    service_account_credentials: str = "GSHEETS_SERVICE_ACCOUNT_CREDENTIALS",
) -> pd.DataFrame:
    """
    Gets an spreadsheet id and tab name as a parameter and tries to read the
    content into a pandas dataframe.
    """
    gsheets = pygsheets.authorize(service_account_env_var=service_account_credentials)
    sheet = gsheets.open_by_key(spreadsheet_id)

    logging.basicConfig(stream=sys.stdout, level=20)

    df = None

    try:
        logging.info(f"Reading data from sheet {sheet_name}...")
        wks_read = sheet.worksheet_by_title(sheet_name)
        df = wks_read.get_as_df()
        logging.info("Read completed.")

    except Exception as exc:
        logging.error(exc)
        logging.error("GSheet could not be read.")

    return df


def query_from_file(engine: Engine, query_path: str) -> pd.DataFrame:
    """
    Execute DB queries from a SQL file.
    """

    try:
        logging.info(f"Reading query from file {query_path}...")
        file = open(query_path, "r")
        query = file.read()
        file.close()

    except Exception as exc:
        logging.error(exc)
        logging.error("Query could not be read.")

    df = None

    try:
        df = query_dataframe(engine, query)
    except Exception as exc:
        logging.error(exc)
        logging.error("Query did not execute.")

    return df
