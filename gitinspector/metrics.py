# coding: utf-8
#
# Copyright © 2012-2015 Ejwa Software. All rights reserved.
#
# This file is part of gitinspector.
#
# gitinspector is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# gitinspector is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gitinspector. If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function
from __future__ import unicode_literals
from localization import N_
from outputable import Outputable
from changes import FileDiff
import comment
import filtering
import interval
import re
import subprocess

__metric_eloc__ = {"java": 500, "c": 500, "cpp": 500, "cs": 500, "h": 300, "hpp": 300, "php": 500, "py": 500, "glsl": 1000,
                   "rb": 500, "js": 500, "sql": 1000, "xml": 1000}

__metric_cc_tokens__ = [[["java", "js", "c", "cc", "cpp"], ["else", "for\s+\(.*\)", "if\s+\(.*\)", "case\s+\w+:",
                                                            "default:", "while\s+\(.*\)"],
                                                           ["assert", "break", "continue", "return"]],
                       [["cs"], ["else", "for\s+\(.*\)", "foreach\s+\(.*\)", "goto\s+\w+:", "if\s+\(.*\)", "case\s+\w+:",
                                 "default:", "while\s+\(.*\)"],
                                ["assert", "break", "continue", "return"]],
                       [["py"], ["^\s+elif .*:$", "^\s+else:$", "^\s+for .*:", "^\s+if .*:$", "^\s+while .*:$"],
                                ["^\s+assert", "break", "continue", "return"]]]

METRIC_CYCLOMATIC_COMPLEXITY_THRESHOLD = 50
METRIC_CYCLOMATIC_COMPLEXITY_DENSITY_THRESHOLD = 0.75

class MetricsLogic:
	def __init__(self):
		self.eloc = {}
		self.cyclomatic_complexity = {}
		self.cyclomatic_complexity_density = {}

		ls_tree_r = subprocess.Popen(["git", "ls-tree", "--name-only", "-r", interval.get_ref()], bufsize=1,
		                             stdout=subprocess.PIPE).stdout

		for i in ls_tree_r.readlines():
			i = i.strip().decode("unicode_escape", "ignore")
			i = i.encode("latin-1", "replace")
			i = i.decode("utf-8", "replace").strip("\"").strip("'").strip()

			if FileDiff.is_valid_extension(i) and not filtering.set_filtered(FileDiff.get_filename(i)):
				file_r = subprocess.Popen(["git", "show", interval.get_ref() + ":{0}".format(i.strip())],
				                          bufsize=1, stdout=subprocess.PIPE).stdout.readlines()

				extension = FileDiff.get_extension(i)
				lines = MetricsLogic.get_eloc(file_r, extension)
				cycc = MetricsLogic.get_cyclomatic_complexity(file_r, extension)

				if __metric_eloc__.get(extension, None) != None and __metric_eloc__[extension] < lines:
					self.eloc[i.strip()] = lines

				if METRIC_CYCLOMATIC_COMPLEXITY_THRESHOLD < cycc:
					self.cyclomatic_complexity[i.strip()] = cycc

				if lines > 0 and METRIC_CYCLOMATIC_COMPLEXITY_DENSITY_THRESHOLD < cycc / float(lines):
					self.cyclomatic_complexity_density[i.strip()] = cycc / float(lines)

	@staticmethod
	def get_cyclomatic_complexity(file_r, extension):
		is_inside_comment = False
		cc_counter = 0

		entry_tokens = None
		exit_tokens = None

		for i in __metric_cc_tokens__:
			if extension in i[0]:
				entry_tokens = i[1]
				exit_tokens = i[2]

		if entry_tokens or exit_tokens:
			for i in file_r:
				i = i.decode("utf-8", "replace")
				(_, is_inside_comment) = comment.handle_comment_block(is_inside_comment, extension, i)

				if not is_inside_comment and not comment.is_comment(extension, i):
					for j in entry_tokens:
						if re.search(j, i, re.DOTALL):
							cc_counter += 2
					for j in exit_tokens:
						if re.search(j, i, re.DOTALL):
							cc_counter += 1
			return cc_counter

		return -1

	@staticmethod
	def get_eloc(file_r, extension):
		is_inside_comment = False
		eloc_counter = 0

		for i in file_r:
			i = i.decode("utf-8", "replace")
			(_, is_inside_comment) = comment.handle_comment_block(is_inside_comment, extension, i)

			if not is_inside_comment and not comment.is_comment(extension, i):
				eloc_counter += 1

		return eloc_counter
