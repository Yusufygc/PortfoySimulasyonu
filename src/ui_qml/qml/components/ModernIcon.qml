import QtQuick
import Qt5Compat.GraphicalEffects
import "../theme"

Item {
    id: root

    property string name: ""
    property alias iconName: root.name
    property alias iconColor: root.color
    property var iconSource: null
    property int size: 16
    property color color: Theme.textPrimary

    implicitWidth: size
    implicitHeight: size

    Image {
        id: srcImg
        anchors.fill: parent
        source: root.iconSource ? root.iconSource : Icons.get(root.name)
        sourceSize.width: root.size * 2
        sourceSize.height: root.size * 2
        fillMode: Image.PreserveAspectFit
        visible: false
        smooth: true
        mipmap: true
    }

    ColorOverlay {
        anchors.fill: srcImg
        source: srcImg
        color: root.color
        visible: srcImg.status === Image.Ready
    }
}
