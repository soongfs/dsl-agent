scenario support_bot {
    initial start;

    state start {
        intent greeting -> "您好，这里是技术支持，请描述您的问题或产品名称。" -> goto triage;
        intent connectivity -> "请确认网络已连接，重启路由器后再试。问题是否解决？" -> goto confirm;
        intent performance -> "请关闭后台程序并重启设备。问题是否解决？" -> goto confirm;
        intent account -> "请检查账号是否登录或密码是否过期。问题是否解决？" -> goto confirm;
        default -> "请简要说明遇到的问题，我会帮您排查。" -> goto triage;
    }

    state triage {
        intent connectivity -> "请确认网络已连接，重启路由器后再试。问题是否解决？" -> goto confirm;
        intent performance -> "请关闭后台程序并重启设备。问题是否解决？" -> goto confirm;
        intent account -> "请检查账号是否登录或密码是否过期。问题是否解决？" -> goto confirm;
        default -> "我需要更多信息：是网络、性能还是账号相关？" -> goto triage;
    }

    state confirm {
        intent confirm -> "很高兴问题已解决，感谢使用。" -> end;
        intent reject -> "好的，我会为您升级到人工或进一步排查，请稍等。" -> end;
        default -> "请回答已解决或未解决。" -> goto confirm;
    }
}
