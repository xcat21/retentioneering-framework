import json
from datetime import datetime
import os
import requests
from IPython.display import HTML, display
import warnings
from retentioneering.analysis.utils import get_shift, get_all_agg, _check_folder


def _get_session(df, order='all', treshold=0.5):
    df = get_shift(df)
    if order == 'all':
        return df
    df['session'] = df.time_to_next_event / 1e6 / 3600 > treshold
    df.session = df.groupby('user_pseudo_id').session.cumsum()
    df = df.join(df.groupby('user_pseudo_id').session.max(), on='user_pseudo_id', rsuffix='_max')
    if order == 'first':
        return df[df.session == 0].copy()
    elif order == 'last':
        return df[df.session == df.session_max].copy()


def plot_graph_api(df, settings, users='all', task='lost', order='all', treshold=0.5,
                   start_event=None, end_event=None):
    warnings.warn('Please use retentioneering.visualization.plot_graph_api instead')
    export_folder, graph_name, set_name = export_tracks(df, settings, users, task, order, treshold,
                                                        start_event, end_event)
    _api_plot(export_folder, graph_name, set_name, plot_type=task)
    path = os.path.join(export_folder, 'graph_plot.pdf')
    display(HTML("<a href='{href}'> {href} </a>".format(href=path)))
    # try:
    #     img = WImage(filename=path)
    #     return img
    # except:
    print("Please check on path behind")


def _api_plot(export_folder, graph_name, set_name, plot_type='lost', download_path=None):
    if not download_path:
        download_path = export_folder

    url = 'http://35.230.23.217:5001/'
    files = {
        'graph': ('graph.csv', open(os.path.join(export_folder, graph_name), 'rb'), 'multipart/form-data'),
        'settings': ('settings.json', open(os.path.join(export_folder, set_name), 'rb'), 'multipart/form-data')}

    r = requests.post(url, files=files, headers={'plot_type': plot_type}, auth=('admin', 'admin'))
    if r.content == 'File was not proceed':
        print("Can't plot graph for this data")
    else:
        with open(os.path.join(download_path, 'graph_plot.pdf'), 'wb') as f:
            f.write(r.content)


def export_tracks(df, settings, users='all', task='lost', order='all', treshold=0.5,
                  start_event=None, end_event=None):
    """
    Visualize trajectories from event clickstream (with Mathematica)

    :param df: event clickstream
    :param settings: experiment config (can be empty dict here)
    :param users: `all` or list of user ids to plot specific group
    :param task: type of task for different visualization (can be `lost` or `prunned_welcome`)
    :param order: depth in sessions for filtering
    :param threshold: threshold for session splitting
    :param start_event: name of start event in trajectory
    :param end_event: name of last event in trajectory

    :param df: pd.DataFrame
    :param settings: dict
    :param users: str or list
    :param task: str
    :param order: int
    :param threshold: float
    :param start_event: str
    :param end_event: str

    :return: None
    """
    settings = _check_folder(settings)
    export_folder = settings['export_folder']
    if task == 'lost' and start_event is None:
        settings['start_event'] = 'welcome_see_screen'
    # else:
    # settings['start_event'] = 'start'
    # df = df.sort_values(['user_pseudo_id', 'event_timestamp'])
    # first = df.groupby('user_pseudo_id', as_index=False).first()
    # first.event_timestamp -= 1
    # first.event_name = 'start'
    # df = df.append(first, ignore_index=True, sort=False)

    agg_list = ['trans_count', 'dt_mean', 'dt_median', 'dt_min', 'dt_max']

    if type(users) != str:
        df = df[df.user_pseudo_id.isin(users)]
        settings['users']['userlist'] = list(users)
    else:
        if settings.get('users') is None:
            settings['users'] = {}
        settings['users']['userlist'] = 'all'

    df = _get_session(df, order=order, treshold=treshold)
    if settings.get('events') is None:
        settings['events'] = {}
    settings['events']['session_order'] = order
    settings['total_count'] = df.user_pseudo_id.nunique()
    df = get_all_agg(df, agg_list)

    settings['events']['session_thr_time'] = treshold * 1e8 * 36

    for i in os.listdir(settings['export_folder']):
        if 'settings' in i:
            set_name = i

    with open(os.path.join(settings['export_folder'], set_name), 'w') as f:
        json.dump(settings, f)
    graph_name = 'graph_{}.csv'.format(datetime.now())
    df.to_csv(os.path.join(export_folder, graph_name), index=False)
    return export_folder, graph_name, set_name
