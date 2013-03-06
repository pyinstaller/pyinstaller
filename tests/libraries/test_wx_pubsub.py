#
# Copyright (C) 2012, Daniel Hyams
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA


from wx.lib.pubsub import pub as Publisher


def on_message(number):
    print 'In the handler'
    if not number == 762:
        raise SystemExit('wx_pubsub failed.')


Publisher.subscribe(on_message, 'topic.subtopic')
Publisher.sendMessage('topic.subtopic', number=762)
