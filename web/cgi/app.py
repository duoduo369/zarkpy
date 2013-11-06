#!/usr/bin/env python
#coding=utf-8
import web
from tool import nginx_uwsgi # nginx_uwsgi负责app.py和nginx之间的通信
import site_helper as sh # 注意，和shell没有关系, 只是一个简写而已:)

# debug模式默认为True，你可以在开发中设置为True，在发布中设置为False
# 当debug为True时, 网页的打开速度可能会很慢
# 当debug为False时，修改模版后必须重启程序才生效
web.config.debug = False

urls = (
# zarkpy reserved
'/cgi/index','pagecontroller.Index', # pagecontroller/Index.py
'/cgi/insert','pagecontroller.Insert', # pagecontroller/Insert.py
'/cgi/update','pagecontroller.Update', # pagecontroller/Update.py
'/cgi/delete','pagecontroller.Delete', # pagecontroller/Delete.py
'/cgi/alert','pagecontroller.Alert', # pagecontroller/Alert.py
'/cgi/login','pagecontroller.user.Login', # pagecontroller/user/Login.py
'/cgi/logout','pagecontroller.user.Login', # pagecontroller/user/Login.py
'/cgi/register','pagecontroller.user.Register', # pagecontroller/user/Register.py
'/cgi/accounts/validate','pagecontroller.user.Validate', # pagecontroller/user/Validate.py
'/cgi/accounts/forget-password','pagecontroller.user.ForgetPassword', # pagecontroller/user/ForgetPassword.py
'/cgi/accounts/reset-password','pagecontroller.user.ResetPassword', # pagecontroller/user/ResetPassword.py
'/cgi/accounts/portrait','pagecontroller.user.Portrait', # pagecontroller/user/Portrait.py
'/cgi/update-portrait','pagecontroller.user.Portrait', # pagecontroller/user/Portrait.py

# admin
'/cgi/insert-richtext-image','editorcontroller.EditorImage', # editorcontroller/EditorImage.py
'/cgi/admin','editorcontroller.Index', # editorcontroller/Index.py
'/cgi/admin/login','editorcontroller.user.Login', # editorcontroller/user/Login.py
'/cgi/admin/logout','editorcontroller.user.Login', # editorcontroller/user/Login.py
'/cgi/admin/update','editorcontroller.Update', # editorcontroller/Update.py
'/cgi/admin/insert','editorcontroller.Insert', # editorcontroller/Insert.py
'/cgi/admin/delete','editorcontroller.Delete', # editorcontroller/Delete.py
'/cgi/admin/model/([^/]+)','editorcontroller.model.List', # editorcontroller/model/List.py
'/cgi/admin/model/([^/]+)/new','editorcontroller.model.Edit', # editorcontroller/model/Edit.py
'/cgi/admin/model/([^/]+)/edit/(\d+)','editorcontroller.model.Edit', # editorcontroller/model/Edit.py
'/cgi/admin/site-config/([-\w]+)','editorcontroller.SiteConfig', # editorcontroller/SiteConfig.py
'/cgi/admin/indent-table/([-\w]+)','editorcontroller.IndentTable', # editorcontroller/IndentTable.py
'/cgi/admin/crop-image','editorcontroller.CropImage', # editorcontroller/CropImage.py
'/cgi/admin/api-index','editorcontroller.ApiIndex', # editorcontroller/ApiIndex.py
'/cgi/admin/report-forms(/[-\w]+)*','editorcontroller.ReportForms', # editorcontroller/ReportForms.py
# oauth2
'/cgi/oauth/login','pagecontroller.oauth.Login', # pagecontroller/oauth/Login.py
'/cgi/oauth/register','pagecontroller.oauth.Register', # pagecontroller/oauth/Register.py
'/api/oauth/login','api.oauth.Login', # api/oauth/Login.py

# api
'/api/get','api.Get', # api/Get.py
'/api/insert','api.Insert', # api/Insert.py
'/api/update','api.Update', # api/Update.py
'/api/delete','api.Delete', # api/Delete.py
'/api/user/register','api.user.Register', # api/user/Register.py
'/api/user/login','api.user.Login', # api/user/Login.py
'/api/user/logout','api.user.Login', # api/user/Login.py
'/api/user/profile','api.user.Profile', # api/user/Profile.py
'/api/user-image','api.UserImage', # api/UserImage.py
)

# init app
app = web.application(urls)
app.notfound = lambda:web.seeother('/html/404.html')

def initSession():
    default_session = dict(is_login=False, id=0, name='', is_admin=False, admin_id=0, admin_name='')
    sh.session = web.session.Session(app, web.session.DiskStore(sh.config.SESSION_PATH), initializer=default_session)

def initRender():
    import datetime
    from tool import subpage_data
    # 模版文件中可以直接访问的变量
    temp_func = {
        'eval':         eval,
        'str':          str,
        'int':          int,
        'len':          len,
        'type':         type,
        'map':          map,
        'all':          all,
        'any':          any,
        'hasattr':      hasattr,
        'getattr':      getattr,
        'input':        web.input,
        'sh':           sh,
        'datetime':     datetime.datetime,
        'subpage_data': subpage_data,
    }

    render = web.template.render

    subpage_path = sh.config.APP_ROOT_PATH + 'web/cgi/subpage'
    sh.autoMkdir(subpage_path)
    temp_func['subpage'] = render(loc=subpage_path, globals=temp_func)
    # 为了能在subpage中使用subpage, 所以这里又render了一次
    temp_func['subpage'] = render(loc=subpage_path, globals=temp_func)
    sh.subpage = temp_func['subpage']

    page_render_path = sh.config.APP_ROOT_PATH + 'web/cgi/page'
    sh.autoMkdir(page_render_path)
    sh.page = render(loc=page_render_path, base='Base', globals=temp_func)
    sh.page_nobase = render(loc=page_render_path, globals=temp_func)

    editor_render_path = sh.config.APP_ROOT_PATH + 'web/cgi/editor'
    sh.autoMkdir(editor_render_path)
    sh.editor = render(loc=editor_render_path, base='Base', globals=temp_func)
    sh.editor_nobase = render(loc=editor_render_path, globals=temp_func)

initSession()
initRender()

import processor
# 添加 processor，上面的先运行
if not sh.config.IS_TEST:
    app.add_processor(processor.profiler.profiler)
    app.add_processor(processor.auto_login.loginByCookie) # 应该放到validate的前面
    app.add_processor(processor.validate.validate)
    app.add_processor(processor.print_api.printDict)
    app.add_processor(processor.file_version.appendVersionNum)

# 仅headers processor用于测试环境
app.add_processor(processor.headers.appendHeader)

if __name__ == "__main__":
    from tool import init_database
    init_database.initTables()
    init_database.initDatas()
    try:
        print 'app running'
        app.run()
    finally:
        db = sh.getDBHelper()
        db.db_dict.close()
        db.db_tuple.close()
