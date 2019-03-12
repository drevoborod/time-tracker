#!/usr/bin/env python3

###
# !!!WARNING!!!
# This file is for testing purposes only! It will create a lot of
# random generated tasks in your actual database! So don't use it
# on production database!
###

import random
from src import core

TASK_LIMIT = 50

SYMBOLS = []
for i in range(65, 91):     # latin uppercase
    SYMBOLS.append(chr(i))
for i in range(97, 122):    # latin lowercase
    SYMBOLS.append(chr(i))


def randword(min_l=6, max_l=20, count=1, table=SYMBOLS):
    random.seed()
    phrase = []
    for w in range(count):
        word = [random.choice(table) for x in range(random.randint(min_l, max_l))]
        phrase.append("".join(word))
    return " ".join(phrase)


core.check_database()
db = core.Db()
for task in range(TASK_LIMIT):
    mi, ma, c = random.randint(5, 10), random.randint(11, 21), random.randint(1, 4)
    taskname = randword(mi, ma, c) + str(task)
    task_id = db.insert_task(taskname)
    db.update_task(task_id, field="description", value=taskname)
    db.update_task(task_id, value=random.randint(145, 9800))
    print("Task %d added" % task)