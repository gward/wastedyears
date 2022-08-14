# wasted years

`wastedyears` is a tool to track the time you spend getting stuff done.
Typically this is for a job that you do on a computer.
It lets you keep track of the tasks you work on,
and the number of times you switch between those tasks.

## Inspirations

Although `wastedyears` is named after
[an Iron Maiden song](https://en.wikipedia.org/wiki/Wasted_Years),
its official theme song is [Pink Floyd's 'Time'](https://en.wikipedia.org/wiki/Time_(Pink_Floyd_song)).
Listen to the lyrics to find out why.

## Tasks

For example, after entering a couple of tasks into `wastedyears`,
your day might look like

    08:57:17 .. 09:03:42 check email
    09:03:55 .. 09:06:15 coffee
    09:06:27 .. 10:15:22 fix bug #321
    10:15:42 .. 10:23:17 check email

If this strikes you as insanely detailed,
and the sort of thing that you would never in a million years care about,
then `wastedyears` might not be the right tool for you.
However, it is carefully optimized to minimize the time spent tracking your time,
in order to maximize the time you spend doing useful productive work.
(Or checking email and getting coffee, as the case may be.)

## Entering tasks

### Command-line (immediate)

There are a couple of ways to enter a task into `wastedyears`:
command-line and GUI.

At the command line, you can run

    wy t check email

to end the previous task and start the next one.

### Command-line (editor)

Or you can simply run

    wy t

to enter a task into a text editor.
The editor will actually show some recent tasks,
so you can copy/paste frequently used items:

    # wy task editor; enter new task here:


    # recent tasks from yesterday:
    amusing email to Andy
    boring email to Bob
    check email

    # recent tasks from today:
    check email
    coffee
    fix bug #321

Once you close your editor,
`wastedyears` adds the first non-comment line to its database as a new task.
Your previous task finishes when you launch the editor,
and the new one starts when you close it.
That's how you get those gaps in the record --
10 seconds here, 15 seconds there, the overhead of recording your tasks.

### GUI

Finally, you can run

    wy gui

to open a small graphical interface that is designed for a quick
get-in-get-out experience.
It's the same basic idea as running a text editor, but more specialized.

## Database

`wastedyears` stores your tasks in a relational database.
Currently only SQLite is supported.
The database is kept in `$XDG_DATA_HOME/wastedyears/wastedyears.sqlite3`.

There are two tables in the database: `tasks` and `words`.
The `tasks` table is fairly obvious:

    task_id  start_ts  end_ts    updated_ts  description
    -------  --------  --------- ----------  ----------------------
          1  08:57:17  09:03:42  08:57:17    check email
          2  09:03:55  09:06:15  09:03:55    coffee
          3  09:06:27  10:15:22  09:06:27    fix bug #321
          4  10:15:42  10:23:17  10:15:42    check email

(All of the `*_ts` columns are actually date-time columns;
I'm showing only the times here to keep things simple.)

The `words` table, which is derived from `tasks`, is where things get more fun:

    word_id  elapsed  word
    -------  -------  -------------------
          1      840  check
          2      840  email
          3      140  coffee
          4     4135  fix
          5     4135  bug
          6     4135  #321

`elapsed` is the total number of seconds spent on tasks that include that word.

Now you can finally prove to your boss that you spend more time fixing bugs thatn getting coffee.
And, after a while, you'll know which bugs took more time.

Not yet solved: do you spend more time _checking_ email or _sending_ email?
I think that will require another derived table to record how strongly
words are correlated with other words.
TBD!

## Queries

There are a couple of command-line tools to list what's in the database:

    wy ls-tasks

    wy ls-words

By default, these list in a simple plain-text format.
Use `--json` to dump the data in JSON.

## Analytics

Once you have built up a few days' (or weeks') worth of tasks,
it's interesting to dig into the data a bit and see what you have been doing.
If you're comfortable with SQL, you can of course do this entirely manually:

    sqlite3 $XDG_DATA_HOME/wastedyears/wastedyears.sqlite3

So far, there is only one built-in analytics command:

    wy rank-words

to list words from "most elapsed time" to least.
