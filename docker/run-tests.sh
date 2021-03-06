#!/bin/sh

# don't want to accidentally test on prod db, always use local db
unset DATABASE_URL

poetry run pytest --ds web.test_settings --reuse-db $@
