from flask import Flask, request
from flask_restplus import Resource, Api, fields
import datetime
import mysql.connector
from decouple import config
from functools import wraps
from werkzeug.contrib.fixers import ProxyFix

mydb = mysql.connector.connect(
  host=config('mysql_host'),
  user=config('mysql_user'),
  password=config('mysql_password'),
  database=config('mysql_database')
)
mycursor = mydb.cursor()

authorizations = {
    'read_write' : {
		'type'  : 'apiKey',
		'in'	: 'header',
		'name'	: 'X-API-KEY'
	}
}
def token_required_read_write(f):
	@wraps(f)
	def wrapped(*args, **kwargs):

		token = None

		if 'X-API-KEY' in request.headers and request.headers['X-API-KEY'] == 'read_write':
			token = request.headers['X-API-KEY']

		if not token:
			return {'message' : 'Token missing or invalid'}, 401
		return f(*args, **kwargs)

	return wrapped


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
api = Api(app, version='1.0', title='TodoMVC API',
    description='A simple TodoMVC API',authorizations = authorizations
)

ns = api.namespace('todos', description='TODO operations')

todo = api.model('Todo', {
    'id': fields.Integer(readonly=True, description='The task unique identifier'),
    'task': fields.String(required=True, description='The task details'),
    'due_by': fields.Date(required=True, description='Due date of the task'),
    'status': fields.String(required=True, description='Status of the task') # Can take up three values, 'finished', 'pending' or 'overdue'
})

status = api.model('Status', {'status': fields.String(required=True)}) # Can take up three values, 'finished', 'pending' or 'overdue'

class TodoDAO(object):
    
        
    def __init__(self):

        mycursor.execute("SELECT * FROM Todolist")
        self.todos = list(map(lambda x:self.convertftuple(x), mycursor.fetchall()))
        self.counter = len(self.todos)
        self.next_index = 0
        for i in self.todos:
            if i['id'] > self.next_index:
                self.next_index =i['id']
        self.counter = len(self.todos)
        

    def convertftuple(self, record):
        todo = {}
        todo['id'],todo['task'],todo['due_by'],todo['status'] = record[0],record[1],datetime.datetime.strftime(record[2], "%Y-%m-%d"),record[3]
        return todo
    
    def get(self, param, type='id'):
        
        mycursor.execute("SELECT * FROM Todolist")
        self.todos = []
        self.todos = list(map(lambda x:self.convertftuple(x), mycursor.fetchall()))
        self.next_index=0
        for i in self.todos:
            if i['id'] > self.next_index:
                self.next_index =i['id']
        self.counter = len(self.todos)
    
        # Returns all the tasks
        if type == 'all':
            return self.todos
        
        # Returns a specific task given its identifier''''
        elif type == 'id':
            for task in self.todos:
                if task['id'] == param:
                    return task
            api.abort(404, "Todo {} doesn't exist".format(param))

        # Returns all the tasks that are due on given date
        elif type == 'due':
            date = param
            tasks = []
            for task in self.todos:
                if task['due_by'] == date:
                    tasks.append(task)
            return tasks
        
        # Returns all the tasks that are already overdue or 
        # are overdue by logic but are yet to be updated in the database. 
        # Also updates the respective records in the database. 
        elif type =='overdue':
            tasks = []
            today = datetime.date.today().strftime('%Y-%m-%d')
            for task in self.todos:
                if(task['status'] == 'overdue'):
                    tasks.append(task)
                elif task['status'] == 'pending' and task['due_by'] < today:
                    task['status'] = 'overdue'
                    sql = "UPDATE Todolist SET status = 'overdue' WHERE id = "+str(task['id'])
                    mycursor.execute(sql)
                    mydb.commit()
                    tasks.append(task)
            return tasks
        
        # Returns all the tasks that are finished
        elif type =='finished':
            tasks = []
            for task in self.todos:
                if task['status'] == 'finished':
                    tasks.append(task)
            return tasks                
    
    def create(self, data):
        task = data
        try:
            datetime.datetime.strptime(task['due_by'], "%Y-%m-%d")
            
            task['id']=self.next_index+1
            self.next_index += 1
            sql = "INSERT INTO Todolist VALUES (%s, %s, %s, %s)"
            val = (task['id'], task['task'], task['due_by'], task['status'])
            mycursor.execute(sql, val)

            mydb.commit()
            return task
        except ValueError:
            return {}

    def update(self, id, data):
        for task in self.todos:
            if(task['id']== id):
                task['status'] = data['status']
                sql = "UPDATE Todolist SET status = (%s) WHERE id = (%s)"
                val = (data['status'], id)
                mycursor.execute(sql, val)

                mydb.commit()
                return task
        api.abort(404, "Todo {} doesn't exist".format(id))
        
    def delete(self, id):
        for task in self.todos:
            if(task['id']== id):
                sql = "DELETE FROM Todolist WHERE id = "+str(id)
                mycursor.execute(sql)
                mydb.commit()
                return task
        api.abort(404, "Todo {} doesn't exist".format(id))

DAO = TodoDAO()


@ns.route('/')
class TodoList(Resource):
    
    '''Shows a list of all todos, and lets you POST to add new tasks'''
    @ns.doc('list_todos')
    @ns.marshal_list_with(todo, skip_none=True)
    def get(self):
        '''List all tasks'''
        return DAO.get('', 'all')

    @ns.doc('create_todo', security='read_write')
    @ns.expect(todo, validate=True)
    @ns.marshal_with(todo, code=201, skip_none=True)
    @token_required_read_write
    def post(self):
        '''Create a new task'''
        return DAO.create(api.payload), 201


@ns.route('/<int:id>')
@ns.response(404, 'Todo not found')
@ns.param('id', 'The task identifier')
class Todo(Resource):
    
    '''Show a single todo item and lets you delete them'''
    @ns.doc('get_todo')
    @ns.marshal_with(todo, skip_none=True)
    def get(self, id):
        '''Fetch a given resource'''
        return DAO.get(id)

    @ns.doc('delete_todo', security='read_write')
    @ns.response(204, 'Todo deleted')
    @ns.marshal_with(todo, skip_none=True)
    @token_required_read_write
    def delete(self, id):
        '''Delete a task given its identifier'''
        return DAO.delete(id)

    @ns.expect(status)
    @ns.doc('update_todo_status', security='read_write')
    @ns.marshal_with(todo, skip_none=True)
    @ns.response(204, 'Todo updated')
    @token_required_read_write
    def put(self, id):
        '''Update a task's status given its identifier'''
        return DAO.update(id, api.payload)


@ns.route('/due/due_date=<string:due_date>')
@ns.param('due_date', 'The desired due date')
class DueDate(Resource):
    @ns.doc('get_todo_due_on_a_specific_date')
    @ns.marshal_with(todo, skip_none=True)
    def get(self, due_date):
        '''Fetches tasks that are due on the given date'''
        return DAO.get(due_date, 'due')


@ns.route('/overdue')
class Overdue(Resource):
    @ns.doc('get_overdue_todo')
    @ns.marshal_with(todo, skip_none=True)
    def get(self):
        '''Fetches tasks that are overdue'''
        return DAO.get('', 'overdue')


@ns.route('/finished')
class Finished(Resource):
    @ns.doc('get_finished_todo')
    @ns.marshal_with(todo, skip_none=True)
    def get(self):
        '''Fetches tasks that are finished'''
        return DAO.get('', 'finished')


if __name__ == '__main__':
    app.run(debug=True)