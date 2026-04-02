from wagtail import hooks


@hooks.register("insert_global_admin_css")
def repository_wagtail_admin_css():
    return ""
