# -*- coding: utf-8 -*-
#
# Copyright (c) 2014-2015 Université Catholique de Louvain.
#
# This file is part of INGInious.
#
# INGInious is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# INGInious is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with INGInious.  If not, see <http://www.gnu.org/licenses/>.
from collections import OrderedDict

import web

from frontend.webapp.pages.course_admin.utils import make_csv, INGIniousAdminPage

class CourseGroupListPage(INGIniousAdminPage):
    """ Course administration page: list of groups """

    def GET(self, courseid):
        """ GET request """
        course, _ = self.get_course_and_check_rights(courseid)
        if not course.is_group_course():
            raise web.notfound()
        else:
            return self.page(course)

    def POST(self, courseid):
        """ POST request """
        course, _ = self.get_course_and_check_rights(courseid)

        if not course.is_group_course():
            raise web.notfound()

        error = ""
        try:
            data = web.input()
            if not data['group_description']:
                error = 'No group description given.'
            else:
                self.database.groups.insert({"course_id": courseid, "users": [], "tutors": [], "size": 2,
                                              "description": data['group_description']})
        except:
            error = 'User returned an invalid form.'

        return self.page(course, error, True)

    def submission_url_generator(self, course, groupid):
        """ Generates a submission url """
        return "/admin/" + course.get_id() + "/download?format=taskid%2Fgroup&groups=" + str(groupid)

    def page(self, course, error="", post=False):
        """ Get all data and display the page """
        grouped_users = list(self.database.groups.aggregate([
            {"$match": {"course_id": course.get_id()}},
            {"$unwind": "$users"},
            {"$group":
                {
                    "_id": "$course_id",
                    "user_list": {"$push": "$users"}
                }
            }]))

        ungrouped_users = len(set(self.user_manager.get_course_registered_users(course, False)) -
                              set(grouped_users[0]["user_list"] if len(grouped_users) > 0 else []))

        groups = OrderedDict([(group['_id'],
                               dict(group.items() +
                                    [("tried", 0),
                                     ("done", 0),
                                     ("url", self.submission_url_generator(course, group['_id']))
                                     ]
                                    )
                               ) for group in self.user_manager.get_course_groups(course)])

        data = list(self.database.submissions.aggregate(
            [
                {
                    "$match":
                        {
                            "courseid": course.get_id(),
                            "groupid": {"$in": groups.keys()}
                        }
                },
                {
                    "$group":
                        {
                            "_id": {"groupid": "$groupid", "taskid": "$taskid"},
                            "done": {"$sum": {"$cond": [{"$eq": ["$result", "success"]}, 1, 0]}}
                        }
                }
            ]))

        for group in data:
            groups[group["_id"]["groupid"]]["tried"] += 1
            groups[group["_id"]["groupid"]]["done"] += 1 if group["done"] else 0

        my_groups, other_groups = [], []
        for group in groups.values():
            if self.user_manager.session_username() in group["tutors"]:
                my_groups.append(group)
            else:
                other_groups.append(group)

        if "csv" in web.input():
            return make_csv(data)

        return self.template_helper.get_renderer().course_admin.group_list(course, [my_groups, other_groups], ungrouped_users, error, post)