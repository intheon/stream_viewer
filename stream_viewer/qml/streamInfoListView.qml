import QtQuick 2.12
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    anchors.fill: parent
    color: "grey"

    ListView {
        id: streamlist
        anchors.fill: parent
        spacing: 1
        model: MyModel
        anchors.margins: 1
        delegate:
            Rectangle {
                color: "lightgrey"
                width: parent.width
                height: 80
                GridLayout {
                    anchors.margins: 2
                    clip: true
                    anchors.fill: parent
                    columns: 2
                    rows: 3
                    Text {
                        text: '<b>Name:</b> ' + name
                        Layout.row: 0; Layout.column: 0
                    }
                    Text {
                        text: '<b>Type:</b> ' + type
                        Layout.row: 0; Layout.column: 1
                    }
                    Text {
                        text: '<b>Host:</b> ' + hostname
                        Layout.row: 1; Layout.column: 0
                    }
                    Text {
                        text: '<b>Channels:</b> ' + channel_count + " (" + channel_format + ")"
                        Layout.row: 1; Layout.column: 1
                    }
                    Text {
                        text: '<b>Nom.Rate:</b> ' + nominal_srate
                        Layout.row: 2; Layout.column: 0
                    }
                    Text {
                        text: '<b>Eff.Rate:</b> ' + effective_rate
                        Layout.row: 2; Layout.column: 1
                    }
//                    Text {
//                        text: uid; elide: Text.ElideRight; Layout.preferredWidth: 150
//                        Layout.row: 2; Layout.column: 2
//                    }
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: streamlist.currentIndex = index
                    onDoubleClicked: OuterWidget.activated(index)  // console.warn("Double clicked " + index)
                }
                ListView.onAdd: {
                    OuterWidget.added(index)
                }
                ListView.onRemove: {
                    OuterWidget.removed()
                }
            }
        ScrollIndicator.vertical: ScrollIndicator { }
//        onCountChanged: console.warn('Model count has changed: ' + count)
//        onCurrentItemChanged: console.warn(streamlist.currentIndex + ' selected')
    }

    Button {
        width: 40
        height: 20
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        Text {
            font.pointSize: 8
            text: "refresh"
            anchors.verticalCenter: parent.verticalCenter
        }
        onClicked: {
            MyModel.refresh();
        }
    }
}
