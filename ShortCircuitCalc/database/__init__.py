# -*- coding: utf-8 -*-
"""This package implements the 'BaseMixin' class, which is necessary to
extend the functionality of the declarative base class 'Base', including:
- automatic generation of table names based on ORM models in the snake_case style;
- automatic generation of primary keys with auto increment.
- the basic implementation of the CRUD interface for working
with the selected database table is presented.

The package also presents ORM models of the database of various electrical devices."""


from ShortCircuitCalc.database.transformers import *
from ShortCircuitCalc.database.cables import *
from ShortCircuitCalc.database.contacts import *
from ShortCircuitCalc.database.install import *
