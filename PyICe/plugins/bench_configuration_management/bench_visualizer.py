"""Bench visualizer plugin.

>>> from PyICe.plugins.bench_configuration_management.bench_visualizer import visualizer

"""
from PyICe.lab_utils.banners import print_banner
import traceback
import subprocess
import os
import base64

try:
    import graphviz
except ImportError:
    graphviz = None  # type: ignore[assignment]
    graphviz_missing = True
else:
    graphviz_missing = False


class visualizer():
    """Visualizer.

    >>> from PyICe.plugins.bench_configuration_management.bench_visualizer import visualizer
    >>> visualizer is not None
    True

    """
    def __init__(self, connections, locations):
        """Initialize visualizer.
        Stores configuration in ``connections``, ``locations`` for use by
        other methods.

        Initializes 2 instance attributes that configure the object's behavior.


        >>> from PyICe.plugins.bench_configuration_management.bench_visualizer import visualizer
        >>> visualizer is not None
        True

        Args:
            connections: Connections to use.
            locations: Locations to use.
        """
        self.locations = locations
        self.connections = connections

    def generate(self, file_base_name, prune=True,
                 file_format='svg', engine='neato', file_location=''):
        """Return the generate.
        Sends the ```` SCPI command to the instrument.
        Sends the ``data:image/`` SCPI command to the instrument.

        Transmits data to the remote endpoint.


        >>> from PyICe.plugins.bench_configuration_management.bench_visualizer import visualizer
        >>> hasattr(visualizer, 'generate')
        True

        Args:
            engine: Engine to use.
            file_base_name: File base name to use.
            file_format: File format to use.
            file_location: File location to use.
            prune: Prune to use.

        Raises:
            Exception: If an unexpected error occurs.
        """
        if file_format.upper() not in ['SVG', 'PNG']:
            raise Exception(
                f"\nBench Visualizer: Sorry don't know how to output file format {file_format}. Try 'svg' or 'png'.\n")
        if graphviz_missing:
            print_banner(
                "Graphviz Python Package not found. Suggest you use a proper PyICe environment as documented on https://github.com/PyICe-ADI/PyICe.")
            return
        f = graphviz.Graph(
            name='Bench Image',
            filename=file_base_name,
            format='svg',
            engine=engine,
            graph_attr=[
                ('bgcolor',
                 'transparent')])
        # f.attr(size='8.5,11') # rankdir='LR',
        f.attr(splines="ortho")  # , imagescale="false")
        #################################################
        #                                               #
        # Add Instruments                               #
        #                                               #
        #################################################
        embed_dictionary = {}
        for instrument in self.locations:
            has_a_connection = False
            for connection in self.connections:
                has_a_connection |= instrument in [
                    connection.terminals[0].owner, connection.terminals[1].owner]
            if has_a_connection or not prune:
                f.node(name=instrument,
                       shape="none",
                       label="",
                       xlabel=instrument if self.locations[instrument]["use_label"] else "",
                       xlp="20",
                       # labelloc        = "b", # bottom - t also allowed
                       # labelfloat      = "true",
                       tooltip=instrument,
                       fontname="Arial",
                       image=self.locations[instrument]["image"],
                       pos=f'{self.locations[instrument]["position"]["xpos"]},{self.locations[instrument]["position"]["ypos"]}',
                       labeldistance="100",
                       fontsize="30")
                binary_fc = open(
                    self.locations[instrument]["image"], 'rb').read()
                base64_utf8_str = base64.b64encode(binary_fc).decode('utf-8')
                ext = self.locations[instrument]["image"].split('.')[-1]
                embed_dictionary[self.locations[instrument]["image"]
                                 ] = f'data:image/{ext};base64,{base64_utf8_str}'

        #################################################
        #                                               #
        # Add Connections                               #
        #                                               #
        #################################################
        for connection in self.connections:
            instr1 = connection.terminals[0].owner
            instr2 = connection.terminals[1].owner
            term1 = connection.terminals[0].type
            term2 = connection.terminals[1].type
            f.edge(instr1,
                   instr2,
                   color="deeppink",
                   penwidth="7",
                   edgetooltip=f"{instr1} : {term1} ↔ {instr2} : {term2}")
            # tailtooltip     = "{term2}",
            # tailURL         = "xxx")
        # f.render()
        # os.remove(file_base_name + ".svg") # This one is junk, incorrect
        # settings. Use a real call to dot.exe.
        try:
            try:
                if file_format.upper() == 'SVG':
                    subprocess.run(["dot",
                                    "-Kneato",
                                    "-n2",
                                    "-Tsvg",
                                    "-o",
                                    file_location + os.sep + file_base_name + ".svg"],
                                   input=f.source,
                                   check=True,
                                   encoding='UTF-8')
                else:
                    subprocess.run(["dot",
                                    "-Kneato",
                                    "-n2",
                                    "-Tpng",
                                    "-o",
                                    file_location + os.sep + file_base_name + ".png"],
                                   input=f.source,
                                   check=True,
                                   encoding='UTF-8')
            except Exception:
                print()
                print_banner(
                    "*** WARNING ***",
                    "Graphviz dot.exe (potentially) not found. Have you installed Graphviz from graphviz.org?",
                    "Ensure that you have a path to graphviz/bin/dot.exe in your environment.")
                print()
                traceback.print_exc()
                return f
            # os.remove(file_base_name)   # Dump the Dot file after the
            # rendered format file is generated.
            benchimage = open(
                file_location +
                os.sep +
                file_base_name +
                ".svg",
                'r')
            bench_string = benchimage.read()
            for image in embed_dictionary.keys():
                bench_string = bench_string.replace(
                    image, embed_dictionary[image])
            benchimage.close()
            embeded = open(
                file_location +
                os.sep +
                file_base_name +
                ".svg",
                'w')
            embeded.write(bench_string)
            embeded.close()
        except Exception as e:
            # if e is subprocess.CalledProcessError
            # print(f'{e.cmd} returned value {e.returncode}')
            print(
                f"There was an issue creating the image file for the bench connections in {__file__}")
            print(e)
            # print(f.source)
            # print(e.stderr)
            print(traceback.print_exc())
        return f
