# create role with user token -> 403
# create role with admin token -> 201
# delete role -> 204
# update role -> 201
# delete role with user token -> 403
# delete role with admin token -> 204
# update role with user token -> 403
# update role with admin token -> 201
# delete master role -> 403
# delete an inexistent role -> 404

# create user with user token -> 403
# create user with admin token -> 201
# delete user -> 204
# update user name -> 201
# update user role -> 201
# update user name with existing name -> 400
# update user role with unexisting role -> 400
# delete master user -> 403
# delete an inexistent user -> 404

# create token with user token -> 403
# create token with admin token -> 201
# delete token -> 204
# delete inexistent token -> 404
# malformed token -> 401
# invalid token -> 401
# expired token -> 401
# check token with user token -> 200
# check token with admin token -> 200
# check inexistent token -> 404


# login with inexistent user -> 401
# login with invalid password -> 401
# login with inexistent role -> 404
# login with invalid role -> 404
# login with master user -> 200
# login with master role -> 200


