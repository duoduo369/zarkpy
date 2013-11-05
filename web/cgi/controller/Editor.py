#coding=utf-8
# 用于后台的页面
# ../testing/controller_test/TestEditor.py
import model
import site_helper as sh

class Editor:
    # 不填写配置时的默认值, 仅用于editor/model/Edit.html页面
    default_menu_config = dict(richtext=[], list_link=[], search=[], layout=[],append_column=[], 
        hidden=[], new_hidden=[], edit_hidden=[], list_hidden=[], list_btn_hidden=[],
        only_show=[], new_only_show=[], edit_only_show=[], list_only_show=[], 
        foreign_input='',
        list_view='', title='', tip='', orderby='', where='' )

    # 根据访问路径path和目录配置，返回此页面的相关配置信息
    # 针对不同的配置会得到不同的数据结构
    def pickPageConfig(self, menu_config, path):
        config = sh.ctrl('IndentTable').contentToDict(menu_config)

        for t1, v1 in config.items():
            for t2, v2 in v1.items():
                if self._matchMenuPath(path, v2):
                    v2._title = [t1, t2]
                    v2 = self._changeType(v2)
                    return v2

        return None

    # 根据default_menu_config的类型改变dict_config的类型
    def _changeType(self, dict_config):
        for k in dict_config.keys():
            v = dict_config[k]
            if k not in ['model', 'url']:
                default = self.default_menu_config.get(k, None)
                if isinstance(v, (str, unicode)) and \
                        isinstance(default, list):
                    dict_config[k] = sh.splitAndStrip(v)
        return dict_config

    def _matchMenuPath(self, path, dict_config):
        if dict_config.has_key('url'):
            if dict_config.url == path:
                return True
        if dict_config.has_key('model'):
            if path.startswith('/admin/model/%s/' % dict_config.model) \
                or path == '/admin/model/%s' % dict_config.model:
                return True
        return False

    def getMenuConfig(self, menu=None, path=None, ):
        if not path:
            path = sh.getEnv('REQUEST_URI').partition('?')[0]
        if not menu:
            menu = self._getEditorMenu()

        menu_config = self.pickPageConfig(menu, path)
        if menu_config:
            for k, v in self.default_menu_config.items():
                menu_config.setdefault(k, v)

        if menu_config and menu_config.where:
            menu_config.where = [c.partition(' ')[::2]
                    for c in sh.splitAndStrip(menu_config.where, '|')]

        if menu_config and menu_config.foreign_input:
            menu_config.foreign_input = dict([
                (a, dict(table_name=b, text_key=c, input_type=d, datas=None))
                for a, b, c, d in [sh.splitAndStrip(i) 
                    for i in sh.splitAndStrip(menu_config.foreign_input, '|')]
            ])

        return menu_config

    # 当后台使用四级目录分类时，_getEditorMenu根据url中的menu参数查找配置
    # 否者直接返回site_helper.editor_config.menu
    def _getEditorMenu(self):
        it = sh.ctrl('IndentTable')
        indents = it.indent(sh.getEditorMenu())
        level = it.getIndentsLevel(indents)

        if level == 3:
            return sh.getEditorMenu()
        elif level == 4:
            menu_name = sh.getUrlParams().get('top_menu', indents[0][0])
            for k,v in indents:
                if k == menu_name or (' ' in k and k.partition(' ')[0] == menu_name):
                    return it.indentsToConfig(v)
        else:
            return ''

    # 更具当前访问url获得后台目录配置, 用于在editor/Base.html中显示
    def getAdminMenuList(self):
        t_ctrl = sh.ctrl('IndentTable')
        menu_list = t_ctrl.indentsToList(t_ctrl.indent(self._getEditorMenu()))
        for title, sub_menu in menu_list:
            for sub_title, page in sub_menu:
                if not page.has_key('url'):
                    model_name = page.get('model', '')
                    assert sh.model(model_name), '后台目录%s配置中缺少url或model名称不正确: %s' % (sub_title, model_name)
                    page.url = '/admin/model/%s' % model_name
        return menu_list

    def getTopMenuTitles(self):
        it = sh.ctrl('IndentTable')
        indents = it.indent(sh.getEditorMenu())
        titles = [i.strip() for i,k in indents] if it.getIndentsLevel(indents) == 4 else []
        return [t.partition(' ')[::2] if ' ' in t else (t, sh.editor_config.index) for t in titles ]

    # 如果后台目录配置是四级的，则返回当前选中的第一级名称，否则返回空''
    def getCurrTopMenuTitle(self):
        it = sh.ctrl('IndentTable')
        indents = it.indent(sh.getEditorMenu())
        if it.getIndentsLevel(indents) == 4:
            return sh.getUrlParams().get('top_menu', indents[0][0]).partition(' ')[0]
        else:
            return ''

    def getChineseColumnName(self):
        config = sh.getSiteConfig('editor_column_ch_name')
        return dict([sh.splitAndStrip(c) for c in config.split('\n') if len(sh.splitAndStrip(c))==2]) \
                if config else sh.storage()
