#coding=utf-8
# ../../controller/Editor.py
import unittest
import site_helper as sh
e_ctrl = sh.ctrl('Editor')
db = sh.getDBHelper()

class TestEditor(unittest.TestCase):

    # sh.ctrl工厂返回的实例是单例模式
    def test_sh_ctrl(self):
        c1 = sh.ctrl('Editor')
        c2 = sh.ctrl('Editor')
        self.assertIs(c1, c2)

    # 根据path中的model名与配置中的model名对比(或url)，获得页面配置
    def test_pickPageConfig(self):
        menu = '''
            内容
                新闻
                    model: News
                其它
                    model: Other
            配置
                排行榜
                    url: /admin/rank
                广告
                    url: /admin/ad
        '''

        path = '/admin/model/News/new'
        target = dict(_title=['内容', '新闻'], model='News')
        self.assertEqual(e_ctrl.pickPageConfig(menu, path), target)
        path = '/admin/model/News/edit/100'
        self.assertEqual(e_ctrl.pickPageConfig(menu, path), target)

        path = '/admin/model/Other/new'
        target = dict(_title=['内容', '其它'], model='Other')
        self.assertEqual(e_ctrl.pickPageConfig(menu, path), target)
        
        path = '/admin/rank'
        target = dict(_title=['配置', '排行榜'], url='/admin/rank')
        self.assertEqual(e_ctrl.pickPageConfig(menu, path), target)
        
        path = '/admin/ad'
        target = dict(_title=['配置', '广告'], url='/admin/ad')
        self.assertEqual(e_ctrl.pickPageConfig(menu, path), target)
        
    # 配置值默认类型为list， 则用空格split
    def test_pickPageConfig_toList(self):
        menu = '''
            内容
                新闻
                    model: News
                    richtext: content paragraph summary
                其它
                    model: Other
                    richtext: content
                    edit_hidden: password text_password
                    list_hidden: password text_password
            数据
                用户
                    model: User
                    edit_only_show: name email
                    list_only_show: name
                    new_title: 管理 用户
                    edit_tip: 不要公布用户的个人信息 ~ ~~!  
        '''

        path = '/admin/model/News/new'
        target = dict(_title=['内容', '新闻'], model='News',
                richtext=['content', 'paragraph', 'summary'])
        self.assertEqual(e_ctrl.pickPageConfig(menu, path), target)

        path = '/admin/model/Other/edit'
        target = dict(_title=['内容', '其它'], model='Other',
                richtext=['content'], edit_hidden=['password', 'text_password'], 
                list_hidden=['password', 'text_password'])
        self.assertEqual(e_ctrl.pickPageConfig(menu, path), target)

        path = '/admin/model/User'
        target = dict(_title=['数据', '用户'], model='User',
                edit_only_show=['name', 'email'], list_only_show=['name'],
                new_title='管理 用户', edit_tip='不要公布用户的个人信息 ~ ~~!')
        self.assertEqual(e_ctrl.pickPageConfig(menu, path), target)

    # getMenuConfig函数返回的数据会继承default_menu_config
    def test_getMenuConfig(self):
        menu = '''
            内容
                新闻
                    model: News
                    where: 被隐藏的新闻 hidden = 'yes' | 热门新闻 hot=1 and hidden='no'
                    foreign_input: Peopleid People name select | Bookid Book title autocomplete
        '''

        path = '/admin/model/News'

        target = dict(_title=['内容', '新闻'], model='News',
                richtext=[], list_link=[], search=[], layout=[], append_column=[],
                hidden=[], new_hidden=[], edit_hidden=[], list_hidden=[], list_btn_hidden=[],
                only_show=[], new_only_show=[], edit_only_show=[], list_only_show=[], 
                list_view='', title='', tip='', orderby='', 
                foreign_input = {
                    'Peopleid': {'table_name': 'People', 'text_key': 'name',
                        'input_type': 'select', 'datas': None},
                    'Bookid': {'table_name': 'Book', 'text_key': 'title',
                        'input_type': 'autocomplete', 'datas': None}
                },
                where = [('被隐藏的新闻',"hidden = 'yes'"),
                    ('热门新闻',"hot=1 and hidden='no'")]
                )

        self.assertEqual(e_ctrl.getMenuConfig(menu, path), target)

    # 根据path找不到配置时返回None
    def test_return_None(self):
        menu = '''
            内容
                新闻
                    model: News
                其它
                    model: Other
        '''
        path = '/admin/model/User/new'
        target = None
        self.assertEqual(e_ctrl.pickPageConfig(menu, path), target)
        self.assertEqual(e_ctrl.getMenuConfig(menu, path), target)

    # 获得后台列名的中英文对照
    def test_getChineseColumnName(self):
        config = '''
            title 标题
            summary 摘要
            error 名称 每行只能有两个单词
            name 名称
        '''
        target = {'title': '标题', 'summary': '摘要', 'name': '名称',}
        sh.setSiteConfig('editor_column_ch_name', config)
        self.assertEqual(e_ctrl.getChineseColumnName(), target)

    # 如果后台目录配置是四级的，则返回第一级名称列表，否则返回空[]
    def test_getTopMenuTitles(self):
        sh.editor_config.menu = '''
        用户中心 /admin/model/User
            管理
                用户
                    model: User
        数据中心
            管理
                图片
                    model: Image
                话题
                    model: Topic
        '''
        target = [('用户中心', '/admin/model/User'), ('数据中心', '/admin')]
        self.assertEqual(e_ctrl.getTopMenuTitles(), target)

        sh.editor_config.menu = '''
        管理
            用户
                model: User
            图片
                model: Image
            话题
                model: Topic
        '''
        target = []
        self.assertEqual(e_ctrl.getTopMenuTitles(), target)
