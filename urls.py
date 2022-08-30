from controllers import *

# FastAPIのルーティング用関数
app.add_api_route('/', index)
app.add_api_route('/admin', admin)
app.add_api_route('/admin/dateinfo', get_dateinfo, methods=['POST'])
app.add_api_route('/admin/dateinfo_error', get_dateinfo_error, methods=['POST'])
app.add_api_route('/admin/monthly_record', get_monthly_record, methods=['POST'])
app.add_api_route('/download_employee', history_download_employee)
app.add_api_route('/download_nonemployee', history_download_nonemployee)
app.add_api_route('/add_holiday', add_holiday, methods=['POST'])