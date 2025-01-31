from collections import defaultdict
import logging
import os
import time
import traceback
from typing import Dict, Iterable, List, Set
import coloredlogs
import joblib
from graphviz import Digraph

from block import Block
from network import Network
from node import Node
from simulator import Simulator
from simulator_parameters import SimulatorParameters
import gi


# Since a system can have multiple versions
# of GTK + installed, we want to make
# sure that we are importing GTK + 3.
gi.require_version("Gtk", "3.0")

from gi.repository import Gtk, GLib

progress_bar_init_success = False

def plot_graph_build(blocks_iter: Iterable[Block], blocks_leafs: List[str] = None) -> Digraph:
    # REFER: http://magjac.com/graphviz-visual-editor/
    #       - Playground for testing and immediate results
    # REFER: https://www.graphviz.org/pdf/dotguide.pdf (Found this from google of "dot language examples")
    #       - Main doc
    # REFER: https://stackoverflow.com/questions/49139028/change-subgraph-cluster-shape-to-rounded-rectangle
    #       - Rounded rectangle
    # REFER: https://graphviz.org/doc/info/shapes.html#record
    #       - Content inside a node
    # REFER: https://ant.design/docs/spec/colors
    #       - Colors
    if blocks_leafs is not None:
        g_logger.debug(f'Tail Count = {len(blocks_leafs)}')

    block_point_count: Dict[str, int] = defaultdict(int)
    for block in blocks_iter:
        block_point_count[block.prev_block_hash] += 1

    g = Digraph('blockchain', node_attr={'shape': 'record', 'style': 'rounded,filled', 'fontname': 'Arial'})
    g.graph_attr['rankdir'] = 'RL'

    for block in blocks_iter:
        point_count = block_point_count[block.curr_block_hash]
        # REFER: https://stackoverflow.com/questions/5466451/how-can-i-print-literal-curly-brace-characters-in-a-string-and-also-use-format
        miner_id: str = '?'
        if len(block.transactions) > 0 and block.transactions[0].id_sender == (-1):
            miner_id = str(block.transactions[0].id_receiver)
        block_label = f'<hash> Hash={block.curr_block_hash[:7]} ' \
                      f'|<link> Link={block.prev_block_hash[:7]} ' \
                      f'| MineTime={block.mine_time:.1f}' \
                      f'| {{Idx={block.index} | Miner={miner_id}}}' \
                      f'| {{NewTxnIncluded={len(block.transactions) - (miner_id != "?")}}}'
        # The below statement is used to check if we have any block hashes which are
        # not leaf blocks but their hashes are present in the leaf blocks list
        if blocks_leafs is not None and block.curr_block_hash in blocks_leafs:
            g_logger.debug(f'{block.curr_block_hash=} , {block.prev_block_hash=} , {point_count=}')
        if block.prev_block_hash == '-1':  # it is genesis block, color=light blue
            g.node(name=block.curr_block_hash, label=block_label, _attributes={'fillcolor': '#40a9ff'})
        elif point_count == 0:  # leaf node, color=light grey
            g.node(name=block.curr_block_hash, label=block_label, _attributes={'fillcolor': '#d9d9d9'})
        elif point_count == 1:  # color=light orange/yellow
            g.node(name=block.curr_block_hash, label=block_label, _attributes={'fillcolor': '#ffd591'})
        else:  # point_count >= 2, branching happens, color=light red
            g.node(name=block.curr_block_hash, label=block_label, _attributes={'fillcolor': '#ff4d4f'})
    for block in blocks_iter:
        if block.prev_block_hash == '-1':
            continue  # do NOTHING for genesis block
        # g.edge(tail_name=f'{block.curr_block_hash}:link',
        #        head_name=f'{block.prev_block_hash}:hash',
        #        _attributes={'weight': '0'})
        g.edge(tail_name=f'{block.curr_block_hash}', head_name=f'{block.prev_block_hash}')
    return g


def plot_graph_combo(nodes_list: List[Node], save_to_file: bool, base_path: str, file_name: str = ''):
    local_blocks_all: Set[Block] = set()
    for node in nodes_list:
        local_blocks_all = local_blocks_all.union(set(node.blocks_all.values()))

    g = plot_graph_build(local_blocks_all, None)

    time.sleep(0.5)
    if file_name == '':
        file_name = f'graph_len{len(nodes_list)}_NodeIndex_{nodes_list[0].node_id:03d}_combo'
    if save_to_file:
        g.view(filename=file_name, directory=base_path)
        # g.view(filename=file_name + '.pdf', directory=base_path)
        # g.view(filename=file_name + '.png', directory=base_path)
    else:
        g.view(directory=base_path)

    time.sleep(0.5)
    g.render()


def plot_graph(node: Node, save_to_file: bool, base_path: str):
    g = plot_graph_build(node.blocks_all.values(), node.blockchain_leafs)

    time.sleep(0.5)
    if save_to_file:
        g.view(filename=os.path.join(base_path, f'graph_NodeIndex_{node.node_id:03d}'))
    else:
        g.view(directory=base_path)

    time.sleep(0.5)
    g.render()


def plot_graph_allone(nodes_list: List[Node], save_to_file: bool, base_path: str, file_name: str = ''):
    block_point_count: Dict[str, int] = defaultdict(int)
    for node in nodes_list:
        for block in node.blocks_all.values():
            block_point_count[str(node.node_id) + '_' + block.prev_block_hash] += 1

    g = Digraph('blockchain', node_attr={'shape': 'record', 'style': 'rounded,filled', 'fontname': 'Arial'})
    g.graph_attr['rankdir'] = 'RL'
    # REFER: https://graphviz.readthedocs.io/en/stable/examples.html
    with g.subgraph() as g_genesis:
        g_genesis.attr(rank='same')
        for node in nodes_list:
            for block in node.blocks_all.values():
                point_count = block_point_count[str(node.node_id) + '_' + block.curr_block_hash]
                miner_id: str = '?'
                if len(block.transactions) > 0 and block.transactions[0].id_sender == (-1):
                    miner_id = str(block.transactions[0].id_receiver)
                block_label = f'Node={node.node_id}' \
                              f'|<hash> Hash={block.curr_block_hash[:7]} ' \
                              f'|<link> Link={block.prev_block_hash[:7]} ' \
                              f'| MineTime={block.mine_time:.1f}' \
                              f'| {{Idx={block.index} | Miner={miner_id}}}' \
                              f'| {{NewTxnIncluded={len(block.transactions) - (miner_id != "?")}}}'
                # The below statement is used to check if we have any block hashes which are
                # not leaf blocks but their hashes are present in the leaf blocks list
                if node.blockchain_leafs is not None and block.curr_block_hash in node.blockchain_leafs:
                    g_logger.debug(f'{block.curr_block_hash=} , {block.prev_block_hash=} , {point_count=}')
                if block.prev_block_hash == '-1':  # it is genesis block, color=light blue
                    g_genesis.node(name=str(node.node_id) + '_' + block.curr_block_hash, label=block_label,
                                   _attributes={'fillcolor': '#40a9ff'})

    for node in nodes_list:
        for block in node.blocks_all.values():
            point_count = block_point_count[str(node.node_id) + '_' + block.curr_block_hash]
            miner_id: str = '?'
            if len(block.transactions) > 0 and block.transactions[0].id_sender == (-1):
                miner_id = str(block.transactions[0].id_receiver)
            block_label = f'Node={node.node_id}' \
                          f'|<hash> Hash={block.curr_block_hash[:7]} ' \
                          f'|<link> Link={block.prev_block_hash[:7]} ' \
                          f'| MineTime={block.mine_time:.1f}' \
                          f'| {{Idx={block.index} | Miner={miner_id}}}' \
                          f'| {{NewTxnIncluded={len(block.transactions) - (miner_id != "?")}}}'
            # The below statement is used to check if we have any block hashes which are
            # not leaf blocks but their hashes are present in the leaf blocks list
            if node.blockchain_leafs is not None and block.curr_block_hash in node.blockchain_leafs:
                g_logger.debug(f'{block.curr_block_hash=} , {block.prev_block_hash=} , {point_count=}')
            if block.prev_block_hash == '-1':  # it is genesis block, color=light blue
                # g_genesis.node(name=str(node.node_id) + '_' + block.curr_block_hash, label=block_label,
                #        _attributes={'fillcolor': '#40a9ff'})
                pass
            elif point_count == 0:  # leaf node, color=light grey
                g.node(name=str(node.node_id) + '_' + block.curr_block_hash, label=block_label,
                       _attributes={'fillcolor': '#d9d9d9'})
            elif point_count == 1:  # color=light orange/yellow
                g.node(name=str(node.node_id) + '_' + block.curr_block_hash, label=block_label,
                       _attributes={'fillcolor': '#ffd591'})
            else:  # point_count >= 2, branching happens, color=light red
                g.node(name=str(node.node_id) + '_' + block.curr_block_hash, label=block_label,
                       _attributes={'fillcolor': '#ff4d4f'})
    for node in nodes_list:
        for block in node.blocks_all.values():
            if block.prev_block_hash == '-1':
                continue  # do NOTHING for genesis block
            # g.edge(tail_name=f'{block.curr_block_hash}:link',
            #        head_name=f'{block.prev_block_hash}:hash',
            #        _attributes={'weight': '0'})
            g.edge(tail_name=f'{node.node_id}_{block.curr_block_hash}',
                   head_name=f'{node.node_id}_{block.prev_block_hash}')

    if file_name == '':
        file_name = f'graph_len{len(nodes_list)}_NodeIndex_{nodes_list[0].node_id:03d}_allone'

    time.sleep(0.5)
    if save_to_file:
        g.view(filename=file_name, directory=base_path)
        # g.view(filename=file_name + '.pdf', directory=base_path)
        # g.view(filename=file_name + '.png', directory=base_path)
    else:
        g.view(directory=base_path)

    time.sleep(0.5)
    g.render()


def simulator_visualization(mySimulator: Simulator) -> None:
    try:
        print()
        print('Enter the input to VIEW/STORE (0/1) and (IndexN/all/allone/combo) '
              'of node of the graph on the same line')
        print('Input format: ^$ , 0 N , 1 (N|all|allone|combo)')
        print('Enter blank line to exit this')
        while view_options := input('Enter: ').split():
            # print(view_options)
            # This is not needed because bool value of empty list if False
            # if len(view_options) == 0:
            #     break
            if len(view_options) == 2:
                if view_options[1] == 'combo':
                    plot_graph_combo(
                        mySimulator.nodes_list,
                        view_options[0] == '1',
                        mySimulator.simulator_parameters.output_path,
                    )
                elif view_options[1] == 'allone':
                    plot_graph_allone(
                        mySimulator.nodes_list,
                        view_options[0] == '1',
                        mySimulator.simulator_parameters.output_path,
                    )
                elif view_options[1] == 'all':
                    if view_options[0] == 0:
                        view_options[0] = '1'
                        g_logger.warning('Saving blockchain tree for all nodes because "all" parameter was passed')
                    for i in mySimulator.nodes_list:
                        plot_graph(i, view_options[0] == '1', mySimulator.simulator_parameters.output_path)
                else:
                    try:
                        if int(view_options[1]) >= mySimulator.simulator_parameters.n_total_nodes:
                            g_logger.warning(
                                f'Total Nodes in the network = {mySimulator.simulator_parameters.n_total_nodes}'
                            )
                            continue
                        plot_graph(mySimulator.nodes_list[int(view_options[1])], view_options[0] == '1',
                                   mySimulator.simulator_parameters.output_path)
                    except Exception as e:
                        g_logger.error(e)
                        g_logger.error(traceback.format_exc())
            else:
                g_logger.warning('Invalid input')
    except Exception as e:
        # REFER: https://stackoverflow.com/questions/3702675/how-to-catch-and-print-the-full-exception-traceback-without-halting-exiting-the
        g_logger.error(e)
        g_logger.error(traceback.format_exc())
    pass


def simulation_analysis(mySimulator: Simulator) -> None:
    """This function is used to analyze the simulation results"""
    global hash_power_median
    for node in mySimulator.nodes_list:
        total_blocks = len(node.blocks_all)

        # Points to the last block of the longest blockchain known to "node.node_id"
        block = node.blocks_all[node.blockchain_leafs[-1]]

        # Total blocks in the longest blockchain known to "node.node_id"
        len_longest_chain = block.index + 1
        # Total blocks in the longest blockchain known to "node.node_id" which are mined it
        node_blocks_longest_chain = 0

        while block.index != 0:
            # First transaction of each block if Mining Reward transaction
            # where the receiver is the miner of the block
            if block.transactions[0].id_receiver == node.node_id:
                node_blocks_longest_chain += 1
            block = node.blocks_all[block.prev_block_hash]

        if node.is_network_fast:
            print("Node type: Fast", sep='\t')
        else:
            print("Node type: Slow", sep='\t')

        if node.node_hash_power_percent > hash_power_median:
            print("CPU Power: High", sep='\t')
        else:
            print("CPU Power: Low", sep='\t')

        print("Ratio  (longest_chain_len/total_block_gen): " +
              str(node_blocks_longest_chain / node.block_generation_count))
    pass


def debug_stats(mySimulator: Simulator):
    g_logger = logging.getLogger(__name__)
    os.chdir('src')
    mySimulator = joblib.load('./blockchains/mySimulator.pkl')
    for node in mySimulator.nodes_list:
        print(node.blockchain_leafs, node.blocks_all[node.blockchain_leafs[-1]].index)
    for node in mySimulator.nodes_list:
        print(len(node.blocks_all))
    for node in mySimulator.nodes_list:
        print(node.blocks_all[node.blockchain_leafs[-1]].index)
    for node in mySimulator.nodes_list:
        max_block_idx = -1
        for block in node.blocks_all.values():
            max_block_idx = max(max_block_idx, block.index)
        print(f'{node.node_id} MAX block index = {max_block_idx}')


# REFER: https://www.geeksforgeeks.org/python-progressbar-in-gtk-3/
# REFER: https://zetcode.com/python/gtk/
class ProgressBarWindow(Gtk.Window):
    def __init__(self):
        #Gtk.Window.__init__(self, title='Simulation Progress')
        #global progress_bar_init_success
        #Gtk.Window.__init__(self, title='Simulation Progress')
        #self.set_border_width(10)

        #vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        #self.add(vbox)

        #self.label = Gtk.Label()
        #self.label.set_text('Initializing...')
        #self.label.set_width_chars(50)
        #vbox.pack_start(self.label, True, True, 0)

        ## Create a ProgressBar
        #self.progressbar = Gtk.ProgressBar()
        #self.progressbar.set_size_request(width=150, height=-1)
        ## self.progressbar.set_text('Initializing...')
        ## self.progressbar.set_show_text(True)
        #vbox.pack_start(self.progressbar, True, True, 0)

        ## Create CheckButton with labels "Show text",
        ## "Activity mode", "Right to Left" respectively
        #button = Gtk.CheckButton(label="Activity mode")
        #button.connect("toggled", self.on_activity_mode_toggled)
        #vbox.pack_start(button, True, True, 0)

        ## REFER: https://docs.gtk.org/glib/func.timeout_add.html
        #self.timeout_id = GLib.timeout_add(500, self.on_timeout, None)
        #self.activity_mode = False
        #self.progress_percent: float = 0.0
        #self.progress_label: str = 'Initializing...'

        #progress_bar_init_success = True
        #
        #self.progress_label = None  # Initialize progress_label
        #self.progressbar = None
        #self.label = None
        Gtk.Window.__init__(self, title='Simulation Progress')
        global progress_bar_init_success
        self.set_border_width(10)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        self.label = Gtk.Label(label="Initializing...")
        vbox.pack_start(self.label, True, True, 0)

        # Initialize progressbar BEFORE setting timeout
        self.progressbar = Gtk.ProgressBar()
        self.progressbar.set_size_request(width=150, height=-1)
        vbox.pack_start(self.progressbar, True, True, 0)

        button = Gtk.CheckButton(label="Activity mode")
        button.connect("toggled", self.on_activity_mode_toggled)
        vbox.pack_start(button, True, True, 0)

        self.activity_mode = False
        self.progress_percent = 0.0
        self.progress_label = "Initializing..."

        # Ensure progressbar is initialized before timeout function
        self.timeout_id = GLib.timeout_add(500, self.on_timeout, None)
        progress_bar_init_success = True

    def update_progress(self, progress_percent, progress_label):
        GLib.idle_add(self._update_progress_idle, progress_percent, progress_label)

    def _update_progress_idle(self, progress_percent, progress_label):
        if self.progressbar:
            self.progressbar.set_fraction(progress_percent)
        if self.label:
            self.label.set_text(progress_label)
        return False  # Run only once per update
    
    def on_activity_mode_toggled(self, button):
        self.activity_mode = button.get_active()
        if self.activity_mode:
            self.progressbar.pulse()
        else:
            self.progressbar.set_fraction(0.0)

    def on_timeout(self, user_data):
        """
        Update value on the progress bar
        """
        if self.activity_mode:
            self.progressbar.pulse()
        else:
            # new_value = self.progressbar.get_fraction() + 0.01
            new_value = self.progress_percent
            if new_value > 1:
                new_value = 1
            self.progressbar.set_fraction(new_value)
            self.label.set_text(self.progress_label)
        return True

    @staticmethod
    def start_progressbar(win: 'ProgressBarWindow'):
        win.connect("destroy", Gtk.main_quit)
        win.show_all()
        Gtk.main()

# def create_and_show_window():
#     win = ProgressBarWindow()
#     win.connect("destroy", Gtk.main_quit)
#     win.show_all()
#     return win


def seconds_to_minsec(t: float) -> str:
    t_min = int(t / 60)
    t_sec = int(t % 60)
    return f'{t_min:02d}:{t_sec:02d}'

def write_node_tree_to_file(node_obj: 'Node', file_name: str):
    global g_logger
    temp_name = file_name
    i = 0
    while os.path.exists(temp_name):
        g_logger.error(f'File already exists: "{file_name}"')
        temp_name = file_name + f'_({i:03d}).txt'
        i += 1
    with open(temp_name, 'w+') as f:
        f.write(node_obj.serialize_blockchain_to_str_v2())
        g_logger.info(f'Successfully written to file_name="{file_name}"')
    pass

def write_all_node_tree_to_file(mySimulator: Simulator):
    for node in mySimulator.nodes_list:
        mySimulator.write_node_tree_to_file(
            node_obj=node,
            file_name=f'{mySimulator.simulator_parameters.output_path}/tree_{node.node_id:03d}.txt'
        )
    pass

def Main(args: Dict):
    global g_logger, progress_bar_init_success
    from threading import Thread

    # REFER: https://stackoverflow.com/questions/2905965/creating-threads-in-python
    # REFER: https://www.geeksforgeeks.org/start-and-stop-a-thread-in-python/
    # GLib.idle_add(create_and_show_window)  # Create window on main thread
    # win = Gtk.main()  # Start GTK main loop (this will block)
    win = ProgressBarWindow()
    #thread = Thread(target=ProgressBarWindow.start_progressbar, args=(win,), daemon=True)
    #thread.start()
    GLib.idle_add(lambda: ProgressBarWindow.start_progressbar(win))

    # Wait for progress bar to setup before executing the upcoming statements
    while (not progress_bar_init_success):
        continue

    time.sleep(0.5)

    win.activity_mode = True
    win.progress_label = 'Initializing...'

    sp = SimulatorParameters()
    sp.load_from_file(args['config'])
    sp.log_parameters()
    mySimulator = Simulator(sp)
    mySimulator.initialize()
    # Create the nodes
    nodes_list = [Node(i, mySimulator, i_hash_power, i_slow_fast, i_malicious, mySimulator.genesis_block)
        for i, (i_hash_power, i_slow_fast, i_malicious) in
        enumerate(mySimulator.params)
    ]
    # Create a connected graph
    # Point 4 of the problem statement PDF
    Network(nodes_list, mySimulator.simulator_parameters)

    # Begin the infinite random transaction creation process
    # While handling an old transaction, a new transaction is created
    for node in nodes_list:
        node.transaction_create(nodes_list)
        node.mining_start()



    win.activity_mode = False
    win.progress_label = 'Executing...'
    last_progress: float = 0.0
    start_time: float = time.time()  # Time in seconds
    while mySimulator.get_global_time() <= sp.execution_time:
        # g_logger.debug(f'{mySimulator.get_global_time()=}')
        win.progress_percent = mySimulator.get_global_time() / sp.execution_time
        if win.progress_percent - last_progress > 0.0001:  # 0.01 / 100
            last_progress = win.progress_percent
            win.progress_label = (f'Executing ({mySimulator.get_global_time():.1f} of {sp.execution_time}, '
                                  f'{seconds_to_minsec(time.time() - start_time)}<'
                                  f'{seconds_to_minsec((time.time() - start_time) / win.progress_percent)})')
        status = mySimulator.execute_next_event()
        if status == False:
            g_logger.info('No events present in the event queue. Exiting...')
            break
        # input()

    # Finish executing all events which were triggered till now
    mySimulator.freeze()
    g_logger.info('Everything freezed except network :)')
    g_logger.info(f'Global Time = {mySimulator.get_global_time()}')

    win.progress_label = 'Everything freezed except network...'
    while True:
        # g_logger.debug(f'{mySimulator.get_global_time()=}')
        status = mySimulator.execute_next_event()
        if status == False:
            g_logger.info('No events present in the event queue. Exiting...')
            break
        # input()
    win.progress_percent = 1.0

    win.progress_label = 'Saving results...'
    if sp.simulator_data_filename != '':
        g_logger.info(f'Saving all the progress of simulator to "{sp.simulator_data_filename}"')
        joblib.dump(mySimulator, os.path.join(sp.output_path, sp.simulator_data_filename), compress=2)
    write_all_node_tree_to_file(mySimulator)

    win.progress_label = 'Visualization in progress...'
    simulator_visualization(mySimulator)
    simulation_analysis(mySimulator)

    g_logger.info(f'Successfully completed executing the simulator for "{sp.execution_time}" seconds')

    win.progress_percent = 1.0
    win.progress_label = 'Completed :)'
    print('Please close the Progress Window')
    thread.join()


if __name__ == '__main__':
    import argparse

    my_parser = argparse.ArgumentParser(prog='simulator.py',
                                        description='Discrete Event Simulator for a P2P Cryptocurrency Network',
                                        epilog='Enjoy the program :)',
                                        prefix_chars='-',
                                        allow_abbrev=False,
                                        add_help=True)
    my_parser.version = '1.1'
    my_parser.add_argument('--version', action='version')
    my_parser.add_argument('-D',
                           '--debug',
                           action='store_true',
                           help='Print debug information')
    my_parser.add_argument('-c',
                           '--config',
                           action='store',
                           type=str,
                           help='Path to the config file',
                           required=True)

    # Execute the parse_args() method
    args: argparse.Namespace = my_parser.parse_args()

    # Initialize "g_logger"
    g_logger = logging.getLogger(__name__)
    # REFER: https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output
    #            - https://github.com/xolox/python-coloredlogs
    if args.debug:
        # g_logger.setLevel(logging.DEBUG)
        coloredlogs.install(fmt='%(levelname)-8s :: [%(lineno)4s] %(name)10s :: %(message)s', level='DEBUG',
                            logger=g_logger)
    else:
        # g_logger.setLevel(logging.INFO)
        coloredlogs.install(fmt='%(levelname)-8s :: [%(lineno)4s] %(name)10s :: %(message)s', level='INFO',
                            logger=g_logger)

    g_logger.debug('Debugging is ON')
    g_logger.debug(f'{args=}')
    # REFER: https://stackoverflow.com/questions/13176173/python-how-to-flush-the-log-django/13753911
    g_logger.handlers[0].flush()

    Main(vars(args))
