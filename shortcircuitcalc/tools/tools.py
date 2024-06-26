# -*- coding: utf-8 -*-
"""
This module provides tools for interacting with catalog databases
and utility tools for the main functionality of the program.

Objects:
    - engine: The SQLAlchemy engine object.
    - metadata: The SQLAlchemy metadata object.

Functions:
    - config_manager: A function that manages configuration parameters.
    - session_scope: Context manager provides a session for executing database operations.

Classes:
    - Base: The SQLAlchemy declarative base child class.
    - Validator: The class for validating the input data.
    - TypesManager: The class-wrapper for the conversion of the value to the needed type.

Decorators:
    - logging_error: Decorator for logging errors in the function.

"""


import logging
import json
import re
import ast
import typing as ty
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from functools import wraps

import sqlalchemy as sa
import sqlalchemy.orm

from shortcircuitcalc.config import (
    ROOT_DIR, CONFIG_DIR, CREDENTIALS_DIR
)


__all__ = (
    'Base', 'engine', 'metadata', 'session_scope',
    'Validator', 'TypesManager', 'config_manager', 'logging_error'
)


logger = logging.getLogger(__name__)


class Validator:
    # noinspection PyUnresolvedReferences
    """
    The class for validating the input data.

    The class for validating the input data in accordance with
    the type annotations specified when creating the dataclasses.

    Attributes:
        default (Any): The default value for the input data.
        log_info (bool): The flag for logging information.
        prefer_default (bool): The flag for preferring default value.

    Sample using dataclass obj True argument with Validator None arg:

    .. code-block:: python

        >> @dataclass
        >> class Person:
        >>     age: float = field(default=Validator())
        >>
        >>
        >> p = Person('10').age
        >> print(p)
        10.0
        >> print(p.__class__.__name__)
        float

    Sample using dataclass obj None argument with Validator True arg:

    ..code-block:: python

        >> @dataclass
        >> class Person:
        >>     age: int = field(default=Validator('1'))
        >>
        >>
        >> p = Person().age
        >> print(p)
        1
        >> print(p.__class__.__name__)
        int

    Sample using dataclass obj False argument with Validator True arg:

    .. code-block:: python

        >> @dataclass
        >> class Person:
        >>     age: Decimal = field(default=Validator('2'))
        >>
        >>
        >> p = Person('').age
        >> print(p)
        2.0
        >> print(p.__class__.__name__)
        Decimal

    Sample using dataclass obj True argument with Validator True arg and prefer_default param:

    .. code-block:: python

        >> @dataclass
        >> class Person:
        >>     age: str = field(default=Validator(3.0, prefer_default=True))
        >>
        >>
        >> p = Person(10).age
        >> print(p)
        3
        >> print(p.__class__.__name__)
        str

    """
    def __init__(self, default=None, log_info: bool = False, prefer_default: bool = False) -> None:
        self._default = default
        self._log_info = log_info
        self._prefer_default = prefer_default
        self._saved_value = None

    def __set_name__(self, owner: ty.Any, name: ty.Any) -> None:
        self._public_name = name
        self._private_name = '_' + name

    def __get__(self, obj: ty.Any, owner: ty.Any) -> ty.Any:
        required_type = ty.get_type_hints(obj)[self._public_name]
        current_type = type(self._saved_value)
        additional = ''

        if required_type == current_type:
            additional = 'NON EMPTY '

        type_error_msg = (f"[GETTER] The type of the attribute '{type(obj).__name__}.{self._public_name}' "
                          f"must be {additional}'{required_type.__name__}', "
                          f"now '{current_type.__name__}'.")

        self._saved_value = getattr(obj, self._private_name)

        if isinstance(self._saved_value, required_type):
            return self._saved_value
        else:
            if self._log_info:
                logger.info(type_error_msg)

    def __set__(self, obj: ty.Any, value: ty.Any) -> None:
        # https://stackoverflow.com/questions/67612451/combining-a-descriptor-class-with-dataclass-and-field
        # Next in Validator.__set__, when the arg argument is not provided to the
        # constructor, the value argument will actually be the instance of the
        # Validator class. So we need to change the guard to see if value is self:
        required_type = ty.get_type_hints(obj)[self._public_name]
        current_type = type(self._saved_value)
        additional = ''

        if required_type == current_type:
            additional = 'NON EMPTY '

        type_error_msg = (f"[SETTER] The type of the attribute '{type(obj).__name__}.{self._public_name}' "
                          f"must be {additional}'{required_type.__name__}', "
                          f"now '{current_type.__name__}'.")
        empty_str_error_msg = (f"[SETTER] Attribute '{type(obj).__name__}.{self._public_name}' "
                               f'must be non empty string.')

        def __set_valid_arg():
            """
            The method return self validated default argument if it is True.

            """
            if isinstance(self._default, str) and self._default or \
                    not (isinstance(self._default, str)) and self._default is not None:
                return required_type(self._default)
            else:
                if isinstance(self._default, str) and not self._default:
                    if self._log_info:
                        logger.info(empty_str_error_msg)

        def __set_obj_arg(arg):
            """
            The method return owner validated argument if it is True.

            """
            if isinstance(arg, str) and arg or \
                    not (isinstance(arg, str)) and arg is not None:
                return required_type(arg)
            else:
                if isinstance(arg, str) and not arg:
                    if self._log_info:
                        logger.info(empty_str_error_msg)

        try:
            if value is self:
                value = __set_valid_arg()

            else:
                if self._prefer_default or not value:
                    value = __set_valid_arg()
                else:
                    value = __set_obj_arg(value)

        except Exception as err:
            logger.error(type_error_msg)
            raise err

        setattr(obj, self._private_name, value)

    def __str__(self) -> str:
        return f'{self._saved_value}'


class TypesManager:
    # noinspection PyUnresolvedReferences
    """
    The class-wrapper for the conversion of the value to the needed type.

    Create and return a new instance of the class.

    Attributes:
        value: The value to be converted to the needed type.
        as_decimal (bool, optional): Whether to convert the value to Decimal type. Defaults to False.
        as_string (bool, optional): Whether to convert the value to string type. Defaults to False.
        quoting (bool, optional): Whether to quote the value. Defaults to False.

    Samples with float / Decimal:

    .. code-block:: python

        >> TypesManager(1.5, as_decimal=True)
        1.5
        >> TypesManager(1.5, as_decimal=True, as_string=True)
        Decimal('1.5')

    Samples with bool / int:

    .. code-block:: python

        >> TypesManager(True, as_decimal=True)
        1.0
        >> TypesManager(False, as_string=True, quoting=True)
        'False'
        >> tm = TypesManager(1, as_string=True)
        >> print(tm)
        1
        >> type(tm.__class__.__name__)
        str

    Samples with string:

    .. code-block:: python

        >> TypesManager('1.5', as_decimal=True)
        1.5
        >> TypesManager('1.5', as_decimal=True, as_string=True, quoting=True)
        "Decimal('1.5')"

    Samples with None:

    .. code-block:: python

        >> TypesManager(None, as_string=True, quoting=True)
        'None'
        >> TypesManager(None)
        None

    """
    def __new__(cls, value: ty.Any, as_decimal: bool = False, as_string: bool = False, quoting: bool = False):
        __new_val = _TypesHandler(value, as_decimal, as_string, quoting)
        if __new_val.value is not None:
            return type(__new_val.value)(__new_val.value)
        else:
            return None


class _TypesHandler:
    """
    The class handles the conversion of the value to the needed type.

    Attributes:
        __value: The value to be converted to the needed type.
        __as_decimal (bool, optional): Whether to convert the value to Decimal type. Defaults to False.
        __as_string (bool, optional): Whether to convert the value to string type. Defaults to False.
        __quoting (bool, optional): Whether to quote the value. Defaults to False.

    Private methods:
        - __types_converting: The method converts the value to the needed type.
        - __type_parser: The method parses the value from string to basic Python type.
        - __to_decimal: The method converts the value to Decimal type.
        - __to_string: The method converts the value to string type.
        - __quote: The method quotes the value.

    """
    def __init__(self, __value: ty.Any, __as_decimal: bool = False, __as_string: bool = False, __quoting: bool = False):
        self.__value = __value
        self.__as_decimal = __as_decimal
        self.__as_string = __as_string
        self.__quoting = __quoting

        self.__types_converting()

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, value: ty.Any):
        self.__value = value

    def __types_converting(self):
        """
        The method converts the value to the needed type.

        """
        if isinstance(self.__value, str):
            self.__type_parser()

        __conversions_options = {
            # dec    str    quot
            (False, False, False): lambda: self,

            (True, False, False): lambda: self.__to_decimal(),
            (False, True, False): lambda: self.__to_string(),
            (False, False, True): lambda: self.__quote(),

            (True, True, False): lambda: self.__to_decimal().__to_string(),
            (False, True, True): lambda: self.__to_string().__quote(),
            (True, False, True): lambda: self.__to_decimal().__quote(),

            (True, True, True): lambda: self.__to_decimal().__to_string().__quote(),

        }

        __conversions_options[self.__as_decimal, self.__as_string, self.__quoting]()

        return self

    def __type_parser(self):
        """
        The method parses the value from string to basic Python type.

        """
        if isinstance(self.__value, str):
            match = re.search(r"Decimal\('([^']+)'\)", self.__value)
            if match:
                self.__value = Decimal(match.group(1))  # decimals parser
            else:
                try:
                    self.__value = ast.literal_eval(self.__value)  # others types parser
                except ValueError:
                    pass

        else:
            msg = f"Cannot parse non-string ({self.__value}, {type(self.__value)})."
            logger.error(msg)
            raise TypeError(msg) from None

        return self

    def __to_decimal(self):
        """
        The method converts the value to Decimal type.

        """
        try:
            if isinstance(self.__value, float):
                self.__value = Decimal(str(self.__value))
            else:
                self.__value = Decimal(self.__value)
        except InvalidOperation:
            msg = f'Cannot convert ({self.__value}, {type(self.__value)}) to Decimal.'
            logger.error(msg)
            raise TypeError(msg) from None

        return self

    def __to_string(self):
        """
        The method converts the value to string type.

        """
        __type_to_string = {
            str: self.__value,
            Decimal: f"Decimal('{self.__value}')",
        }

        try:
            self.__value = __type_to_string[type(self.__value)]
        except KeyError:
            self.__value = str(self.__value)

        return self

    def __quote(self):
        """
        The method quotes the value.

        Also, if the value is already quoted, method returns double-quoted value.

        """
        try:
            if "\'" in self.__value:
                self.__value = f'"{self.__value}"'
            else:
                self.__value = f"'{self.__value}'"
        except TypeError:
            msg = f"Cannot quoting ({self.__value}, {type(self.__value)}), use also 'to_string' option."
            logger.error(msg)
            raise TypeError(msg) from None

        return self


def config_manager(param: str, new_val: ty.Any = None) -> ty.Any:
    """
    A function that manages configuration parameters.

    This function reads the configuration file specified by CONFIG_DIR, searches for the
    specified configuration parameter, and returns its current value. If a new value is
    provided, the function updates the configuration file with the new value and prints a
    message indicating the change. If the configuration file does not exist, a FileNotFoundError
    is raised.

    Args:
        param (str): The name of the configuration parameter to manage.
        new_val (str, optional): The new value for the configuration parameter. Defaults to False.

    Returns:
        Any: The current value of the configuration parameter if value is provided,
        or None if the configuration parameter does not exist.

    Raises:
        FileNotFoundError: If the configuration file specified by CONFIG_DIR does not exist.

    Note:
        The configuration file is assumed to be in UTF-8 encoding.

    Getting param sample:

    .. code-block:: python

        >> config_manager('SYSTEM_PHASES')

    Setting param samples:

    .. code-block:: python

        >> config_manager('SQLITE_DB_NAME', 'test.db')
        >> config_manager('ENGINE_ECHO', True)

    """
    pattern = re.compile(rf'(?P<name>{param}) = (?P<value>.+)\n')
    config_file = open(CONFIG_DIR, 'r+', encoding='UTF-8')
    current_config_data = config_file.read()
    matched_param = re.search(pattern, current_config_data)

    if matched_param is not None and new_val is None:
        return TypesManager(matched_param.group('value'))
    elif matched_param is None:
        return None
    else:
        __formats = {
            str: lambda: TypesManager(new_val, quoting=True),
        }

        try:
            new_val = TypesManager(new_val)
            new_val = __formats[type(new_val)]()
        except KeyError:
            new_val = TypesManager(new_val, as_string=True)

        updated_config_data = current_config_data.replace(
            f"{matched_param.group('name')} = {matched_param.group('value')}",  # noqa
            f"{matched_param.group('name')} = {new_val}", 1)  # noqa
        config_file.seek(0)
        config_file.truncate()
        config_file.write(updated_config_data)
        config_file.close()
        logger.warning(f'Config params changed: now {param} = {new_val}!')


def db_access() -> str:
    """
    Returns a string representing the database connection URL based on the existing configuration.

    This function checks the existing configuration to determine the type of database connection
    to use. If the configuration specifies a MySQL database, it opens the credentials file, loads
    the necessary data, and constructs the MySQL engine string. If the configuration specifies a
    SQLite database, it returns the SQLite engine string.

    Returns:
        str: The database connection URL.

    """
    def __mysql_access() -> str:
        """
        Creates a connection to the MySQL database.

        Service method, opens the credentials file, loads the necessary data,
        and constructs the MySQL engine string.

        Returns:
            str: The MySQL engine string.

        """
        logger.info('Accessing MySQL database...')
        logger.info('Credentials initializing...')

        try:
            with open(CREDENTIALS_DIR, 'r', encoding='UTF-8') as file:
                temp = json.load(file)['credentials']
                login, password, db_name = temp['login'], temp['password'], temp['db_name']
                engine_string = f'mysql+pymysql://{login}:{password}@localhost/{db_name}?charset=utf8mb4'

            logger.info('Connected to MySQL database.')

            if config_manager('DB_EXISTING_CONNECTION') != 'MySQL':
                config_manager('DB_EXISTING_CONNECTION', 'MySQL')

            return engine_string

        except FileNotFoundError:
            logger.error('Credentials file for MySQL database not found! '
                         'Try to choose another connection.')

    def __sqlite_access() -> str:
        """
        Creates a connection to the SQLite database.

        Service method, returns the SQLite engine string.

        Returns:
            str: The SQLite engine string.

        """
        logger.info('Connected to SQLite database.')

        if config_manager('DB_EXISTING_CONNECTION') != 'SQLite':
            config_manager('DB_EXISTING_CONNECTION', 'SQLite')

        return f"sqlite:///{ROOT_DIR}/{config_manager('SQLITE_DB_NAME')}"

    connection_types = {
        'MySQL': __mysql_access,
        'SQLite': __sqlite_access
    }

    if not hasattr(db_access, 'engine_string'):
        try:
            db_access.engine_string = connection_types[config_manager('DB_EXISTING_CONNECTION')]()
            return db_access.engine_string

        except (Exception,):
            logger.error('Something wrong with access to current database. '
                         'Try to choose another connection and restart program.')
    else:
        return db_access.engine_string


Base = sa.orm.declarative_base()
engine = sa.create_engine(url=db_access(), echo=config_manager('ENGINE_ECHO'))
metadata = sa.MetaData()
Session = sa.orm.sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope(logs: bool = True) -> None:
    """
    Context manager provides a session for executing database operations.

    Func yield:
        - A session object for executing database operations.

    Args:
        logs (bool, optional): Whether to log errors. Defaults to True.

    Raises:
        Exception: If an error occurs during the execution of the database operations.

    """
    session = Session()
    try:
        if config_manager('DB_EXISTING_CONNECTION') == 'SQLite':
            session.execute(sa.text("PRAGMA foreign_keys = ON;"))
        yield session
        session.commit()
    except sa.exc.OperationalError as err:
        session.rollback()
        if logs:
            logger.error(err)
        raise err
    finally:
        session.close()


def logging_error(func: ty.Callable) -> ty.Callable:
    """
    Decorator for logging errors in the function.

    Args:
        func (ty.Callable): The function to be decorated.

    Returns:
        ty.Callable: The decorated function.

    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as err:
            logger.error(err)

    return wrapper
