                if (args[i] == "-recipient-script-name-check")
                {
                    try
                    {
                        if (i + 2 != args.size())
                            throw std::runtime_error("usage: -recipient-script-name-check cp_zmb");
                        observe_recipient_script_names(args[i + 1]);
                        fflush(nullptr);
                        std::quick_exit(EXIT_SUCCESS);
                    }
                    catch (const std::exception& error)
                    {
                        ZONETOOL_ERROR("Script-name observation refused: %s", error.what());
                    }
                    catch (...)
                    {
                        ZONETOOL_ERROR("Script-name observation refused with an unknown error");
                    }
                    fflush(nullptr);
                    std::quick_exit(EXIT_FAILURE);
                }
