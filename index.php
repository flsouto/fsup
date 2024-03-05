<?php

echo passthru("python3 callback.py ".$_REQUEST['code']." 2>&1");
