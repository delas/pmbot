import json
import os
import datetime
import time
import tempfile

from pm4py.objects.log.importer.xes import factory as xes_importer
from pm4py.objects.log.exporter.xes import factory as xes_exporter

from pm4py.algo.discovery.alpha import factory as alpha_miner
from pm4py.visualization.petrinet import factory as vis_factory
from pm4py.visualization.graphs import factory as graphs_vis_factory
from pm4py.util import constants
from pm4py.visualization.common import save as gsave
from pm4py.statistics.traces.log import case_statistics
import pm4py.objects.log.util

from pm4py.algo.discovery.dfg import factory as dfg_factory
from pm4py.visualization.dfg import factory as dfg_vis_factory

from pm4py.util import constants
from pm4py.algo.filtering.log.attributes import attributes_filter

from pm4py.visualization.heuristics_net import factory as hn_vis_factory
from pm4py.algo.discovery.heuristics import factory as heuristics_miner
from pm4py.visualization.petrinet import factory as pn_vis_factory


def get_properties(chat_id):
    if os.path.isfile("configs/" + str(chat_id) + ".json"):
        return json.load(open("configs/" + str(chat_id) + ".json", "r"))
    return dict()


def get_property(chat_id, prop):
    return get_properties(chat_id)[prop]


def set_property(chat_id, prop, value):
    p = get_properties(chat_id)
    p[prop] = value
    p["last_update"] = str(datetime.datetime.now())
    json.dump(p, open("configs/" + str(chat_id) + ".json", "w"))


def get_log_filename(chat_id, filtered=False):
    if filtered:
        return "logs/" + str(chat_id) + "_filtered.xes.gz"
    else:
        return "logs/" + str(chat_id) + "_current.xes.gz"


def set_log(chat_id, log, original_name):
    filename = get_log_filename(chat_id)
    open(filename, 'wb').write(log)
    set_property(chat_id, "current_log", filename)
    set_property(chat_id, "log_original_name", original_name)


def get_current_log(chat_id):
    return xes_importer.import_log(get_property(chat_id, "current_log"))


def describe_log(chat_id):
    log = get_current_log(chat_id)
    filename = None
    filename2 = None
    # case duration
    try:
        x, y = case_statistics.get_kde_caseduration(log, parameters={
            constants.PARAMETER_CONSTANT_TIMESTAMP_KEY: "time:timestamp"})
        gviz = graphs_vis_factory.apply_plot(x, y, variant="cases")
        new_file, filename = tempfile.mkstemp(suffix="png")
        graphs_vis_factory.save(gviz, filename)
    except OSError:
        pass

    # events over time
    try:
        x, y = attributes_filter.get_kde_date_attribute(log, attribute="time:timestamp")
        gviz2 = graphs_vis_factory.apply_plot(x, y, variant="dates")
        new_file2, filename2 = tempfile.mkstemp(suffix="png")
        graphs_vis_factory.save(gviz2, filename2)
    except OSError:
        pass

    return {"traces": len(log),
            "acts_freq": pm4py.objects.log.util.log.get_event_labels_counted(log, "concept:name"),
            "case_duration": filename,
            "events_over_time": filename2}


def get_all_activities(chat_id):
    log = get_current_log(chat_id)
    return pm4py.objects.log.util.log.get_event_labels(log, "concept:name")


def bot_alpha_miner(chat_id):
    log = get_current_log(chat_id)
    net, initial_marking, final_marking = alpha_miner.apply(log)
    gviz = vis_factory.apply(net, initial_marking, final_marking)
    new_file, filename = tempfile.mkstemp(suffix="png")
    vis_factory.save(gviz, filename)
    return filename


def bot_dfg(chat_id):
    log = get_current_log(chat_id)
    dfg = dfg_factory.apply(log)
    gviz = dfg_vis_factory.apply(dfg, log=log, variant="frequency")
    new_file, filename = tempfile.mkstemp(suffix="png")
    dfg_vis_factory.save(gviz, filename)
    return filename


def bot_hm(chat_id, dependency_threshold = 0.99):
    log = get_current_log(chat_id)
    heu_net = heuristics_miner.apply_heu(log, parameters={"dependency_thresh": dependency_threshold})
    gviz = hn_vis_factory.apply(heu_net)
    new_file, filename = tempfile.mkstemp(suffix="png")
    hn_vis_factory.save(gviz, filename)

    net, im, fm = heuristics_miner.apply(log, parameters={"dependency_thresh": dependency_threshold})
    gviz = pn_vis_factory.apply(net, im, fm)
    new_file2, filename2 = tempfile.mkstemp(suffix="png")
    pn_vis_factory.save(gviz, filename2)

    return [filename, filename2]


def filter_per_activities_to_keep(chat_id, activities):
    log = get_current_log(chat_id)
    tracefilter_log_pos = attributes_filter.apply_events(log, activities, parameters={constants.PARAMETER_CONSTANT_ATTRIBUTE_KEY: "concept:name", "positive": True})
    xes_exporter.export_log(tracefilter_log_pos, get_log_filename(chat_id, True)[:-3], parameters={"compress": True})
    set_property(chat_id, "current_log", get_log_filename(chat_id, True))
