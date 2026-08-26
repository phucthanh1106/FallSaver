# on_conflict="ipv4, user_id" 
"Look at the user_id and the ipv4 columns. If you find an existing row in the database that has this exact same combination of user and IP address, do not create a duplicate and do not throw an error. Instead, just update that existing row with my new data. If that combination doesn't exist yet, go ahead and insert a brand new row."

# index
- create unique index cameras_user_index_unique => By adding the word unique, you are telling PostgreSQL: "Create a fast lookup table, but also act as a bouncer. If anyone tries to insert a row that already exists in this index, reject it.

- on public.cameras(user_id, "index")
=> This creates a Composite Unique Constraint. It ties the user_id and the "index" columns together to enforce a very specific rule:
+ User A can save Camera 102.
+ User B can save Camera 102.
+ But User A CANNOT save a second Camera 102.



