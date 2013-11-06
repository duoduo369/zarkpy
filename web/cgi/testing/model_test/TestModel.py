#coding=utf-8
# ../../model/Model.py
import unittest
import site_helper as sh

db = sh.getDBHelper()
image_model = sh.model('Image')
image_model.use_convert = False # 图片数据是假的，所以不对图片做处理
user_model = sh.model('User')
test_image = sh.storage(dict(filename='c://file.jpg', value='test file', imagetype='jpg'))

# 对Model.py的基础功能进行测试，因为Model本身没有对应的表
# 所以会使用其它子类代替, 比如Image和User
class TestModel(unittest.TestCase):

    # setUp为运行每个test_*函数之前都会运行的初始化函数
    def setUp(self):
        db.executeQuery('delete from %s' % image_model.table_name)
        db.executeQuery('delete from %s' % user_model.table_name)

    # sh.model工厂返回的数据是单例模式
    def test_sh_model(self):
        image_model2 = sh.model('Image')
        self.assertIs(image_model2, image_model)
        # 指明decorator参数时则不使用单例模式
        decorator = [('Orderby', dict(orderby='{$primary_key} desc')),]
        image_model3 = sh.model('Image', decorator)
        self.assertIsNot(image_model3, image_model)
        image_model4 = sh.model('Image', decorator)
        self.assertIsNot(image_model4, image_model3)

    def test_get(self):
        id = db.insert('insert into Image (data_name) values (%s)', ('test_image'))
        self.assertEqual(image_model.get(id).data_name, 'test_image')
        item1 = image_model.get(id)
        item2 = image_model.get(id)
        # 每次get都会返回不同的拷贝, 如果返回了同一个"指针"，将会给网站带来复杂的耦合与隐性bug
        self.assertIsNot(item1, item2)

    def test_insert(self):
        data = {'data_name': 'test_image', image_model.image_key: test_image}
        id = image_model.insert(data)
        self.assertEqual(image_model.get(id).data_name, 'test_image')

    def test_replaceInsert(self):
        id1 = user_model.insert(dict(email='sdjllyh@gmail.com', name='sdjl', password='123456', register_ip='127.0.0.1'))
        old_count = len(user_model.all())
        id2 = user_model.replaceInsert(dict(email='sdjllyh@gmail.com', name='sdjl2', password='abcdef', register_ip='127.0.0.2'))
        self.assertEqual(len(user_model.all()), old_count)
        self.assertEqual(user_model.get(id1), None)
        self.assertEqual(user_model.get(id2).name, 'sdjl2')

    def test_update(self):
        id = db.insert('insert into Image (data_name) values (%s)', ('test_image'))
        image_model.update(id, dict(data_name='updated'))
        self.assertEqual(image_model.get(id).data_name, 'updated')

    def test_delete(self):
        id = db.insert('insert into Image (data_name) values (%s)', ('test_image'))
        result = image_model.delete(id)
        self.assertEqual(result, 1)
        self.assertEqual(image_model.get(id), None)

    def test_gets(self):
        id1 = db.insert('insert into Image (data_name) values (%s)', ('test_image'))
        id2 = db.insert('insert into Image (data_name) values (%s)', ('test_image'))
        id3 = db.insert('insert into Image (data_name) values (%s)', ('test_image'))
        items = image_model.gets([id1, id2, id3])
        self.assertEqual(image_model.get(id1).id, items[0].id)
        self.assertEqual(image_model.get(id2).id, items[1].id)
        self.assertEqual(image_model.get(id3).id, items[2].id)

    def test_getOneByWhere(self):
        id1 = db.insert('insert into Image (data_name, data_id) values (%s, %s)', ('test_image', 123))
        item = image_model.getOneByWhere('data_name=%s and data_id=%s', 'test_image', 123)
        self.assertEqual(id1, item.id)

    # 分别对传入all函数的不同env进行测试
    def test_all(self):
        # 测试where
        id1 = db.insert('insert into Image (data_name, data_id) values (%s, %s)', ('test_image', 123))
        env = sh.storage()
        env.where = ['data_name=%s and data_id=%s', 'test_image', 123]
        self.assertEqual(image_model.all(env)[0].id, id1)

        # 测试where + select
        env.select = 'data_name'
        items = image_model.all(env)
        self.assertEqual(items[0].data_name, 'test_image')
        self.assertTrue(not items[0].has_key('data_id'))

        # 测试orderby
        id2 = db.insert('insert into Image (data_name, data_id) values (%s, %s)', ('image2', 456))
        assert id2 > id1
        env = sh.storage(dict(orderby='Imageid desc'))
        items = image_model.all(env)
        self.assertTrue(items[0].id > items[1].id)

        # 测试limit
        env = sh.storage(dict(limit=[0, 1]))
        items = image_model.all(env)
        self.assertTrue(len(items) == 1)

        # 测试distinct
        id3 = db.insert('insert into Image (data_name, data_id) values (%s, %s)', ('image2', 789))
        env = sh.storage(dict(distinct=True, where=['data_name=%s', 'image2']))
        items = image_model.all(env)
        self.assertTrue(len(items) == 2)

        # 测试from + select
        uid = user_model.insert(dict(email='sdjllyh@gmail.com', name='sdjl', password='123456', register_ip='127.0.0.1', Imageid=id3))
        env = sh.storage()
        env['from'] = 'User u join Image i on u.Imageid=i.Imageid'
        env.select = 'u.email email, i.data_id data_id'
        env.where = ['email=%s', 'sdjllyh@gmail.com']
        items = image_model.all(env)
        self.assertTrue(len(items) == 1)
        self.assertEqual(items[0].email, 'sdjllyh@gmail.com')
        self.assertEqual(items[0].data_id, 789)

    def test_getCount(self):
        db.insert('insert into Image (data_name, data_id) values (%s, %s)', ('test_image', 123))
        db.insert('insert into Image (data_name, data_id) values (%s, %s)', ('test_image', 123))
        db.insert('insert into Image (data_name, data_id) values (%s, %s)', ('test_image', 456))
        env = sh.storage(dict(where=['data_id=%s', 123]))
        self.assertEqual(image_model.getCount(env), len(image_model.all(env)))

    def test_getColumnTypes(self):
        # 使用默认列名, 返回字典字段类型
        types = image_model.getColumnTypes()
        self.assertEqual(types.data_name,
            {'type':'str', 'accurate_type':'varchar', 'length': 20, 'null': False, 'default': '' })
        self.assertEqual(types['data_id'],
            {'type':'int', 'accurate_type':'int', 'null': False, 'default': 0, 'unsigned': True})
        self.assertEqual(types['url'],
            {'type':'str', 'accurate_type':'varchar', 'length': 100, 'null': False, 'default': '' })
        # 可以主动传入参数，并可返回time类型
        types = user_model.getColumnTypes(['created', 'dead'])
        self.assertEqual(len(types.keys()), 3) # 还有 __column_names
        self.assertEqual(types['created'],
            {'type':'time', 'accurate_type':'timestamp', 'null': False, 'default': '' })
        self.assertEqual(types['dead'],
            {'type':'enum', 'options':['yes', 'no'], 'accurate_type':'enum', 'null': False, 'default': 'no' })

    # createTable可以根据table_name和table_template创建数据表
    def test_createTable(self):
        new_image_model = sh.model('Image')
        new_image_model.table_name = 'ImageTempForTest'
        new_image_model.createTable()
        self.assertTrue(db.isTableExists('ImageTempForTest'))
        columns = db.getTableColumns('ImageTempForTest')
        self.assertTrue('ImageTempForTestid' in columns)
        self.assertTrue('data_name' in columns)
        new_image_model.table_name = 'Image' # model是单例模式,若不改回则会影响其它测试

    # increaseCreateTable函数能新建字段，但不删除原有字段
    def test_increaseCreateTable(self):
        old_template = image_model.table_template
        image_model.table_template = image_model.table_template.replace('data_name', 'data_name_for_test')
        image_model.increaseCreateTable()
        self.assertTrue(db.isColumnExists('Image', 'data_name_for_test'))
        self.assertTrue(db.isColumnExists('Image', 'data_name')) # 保留原有字段
        image_model.table_template = old_template

    # 返回数据能够根据id自动关联
    def test_autoRelated(self):
        # 可以通过User表中的Imageid字段, 用user数据取得一个image数据
        iid1 = db.insert('insert into Image (data_name, data_id) values (%s, %s)', ('related', 123))
        uid1 = user_model.insert(dict(email='sdjllyh@gmail.com', name='sdjl', password='123456', register_ip='127.0.0.1', Imageid=iid1))
        user = user_model.get(uid1)
        self.assertEqual(user.image.data_name, 'related')

        # 可以通过User表中的Imageid字段, 用image数据取得多个user数据(加s)
        uid2 = user_model.insert(dict(email='squallsdjl@gmail.com', name='squallsdjl', password='123456', register_ip='127.0.0.1', Imageid=iid1))
        image = image_model.get(iid1)
        self.assertEqual(len(image.users), 2) # 关联到两个user数据
        self.assertEqual(image.users[0].email, 'sdjllyh@gmail.com') # Userid升序
        self.assertEqual(image.users[1].email, 'squallsdjl@gmail.com')

    # replaceAttr函数能用model的属性值替换sql query中的变量
    def test_replaceAttr(self):
        query1 = 'select {$primary_key} from {$table_name} where {$table_name}id = %s'
        query2 = 'select Imageid from Image where Imageid = %s'
        self.assertEqual(image_model.replaceAttr(query1), query2)
