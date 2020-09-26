/**
        class Chat
        @constructor
**/
voyc.Chat = function() {
        this.chatcontainer = {};
        this.chatscroller = {};
        this.chatcontent = {};
        this.eEntry = {};
        this.users = [];
        this.idhost = 0;
        this.idguest = 0;
}

voyc.Chat.containertemplate = `
        <div id='chatscroller'>
                <div id='chatcontent'></div>
        </div>
        <div id='chatfoot'>
                <table id='chatentry' class='chatentry'>
                        <td><textarea id='guestpost'></textarea></td>
                        <td><div id='mchoices'>yes no</div></td>
                        <td><button id='guestpostbtn'>></button></td>
                </table>
        </div>
`;

voyc.Chat.posttemplate = "<div class='chatline clearfix'><div class='chatuser f%side%'>%user%</div><div class='chatmsg f%side%'>%message%</div><div class='chattime f%side%'>%time%</div></div>";
voyc.Chat.entrytemplate = "";

voyc.Chat.prototype.setup = function(container) {
        this.chatcontainer = container;
        this.chatcontainer.innerHTML = voyc.Chat.containertemplate;
        this.chatscroller = document.getElementById('chatscroller');
        this.chatcontent = document.getElementById('chatcontent');

        var self = this;
        document.getElementById('guestpostbtn').addEventListener('click', function(e) {
                var s = document.getElementById('guestpost').value;
                //self.post(self.idguest, s);
				voyc.ws.send(s)
                document.getElementById('guestpost').value = '';
        }, false);
        document.getElementById('guestpost').addEventListener('keydown', function(e) {
                if (e.keyCode == 13) {
                        document.getElementById('guestpostbtn').click();
                        e.preventDefault();
                }
        }, false);
}

voyc.Chat.prototype.resize = function(height) {
        this.chatscroller.style.height = height - document.getElementById('chatfoot').offsetHeight + 'px';
}
voyc.Chat.prototype.addUser = function(name, host, guest) {
        var ndx = this.users.length;
        var id = ndx + 1;
        var host = host || false;
        var guest = guest || false;
        this.users.push({id:id, name:name, host:host, guest:guest});
        if (host) {
                this.idhost = id;
        }
        if (guest) {
                this.idguest = id;
        }
        return id;
}

voyc.Chat.prototype.changeHost = function(id) {
        this.idhost = id;
}

/**
        method post()
        If multiple humans are using this,
        each human will have his own instance of the screen,
        with himself on the right, and the others on the left.
        
        In normal usage, Samantha is the host and I am the guest.
        Sam is on the left, I am on the right.
**/
voyc.Chat.prototype.post = function(id, message, mchoice) {
        var user = this.users[id - 1];
        var side = 'right';
        var name = '';
        if (id == this.idhost) {
                side = 'left';
                name = user.name + ':';
        }

        var dtime = new Date();
        var hh = dtime.getHours();
        var mm = dtime.getMinutes();
        var smm = mm.toString();
        smm = (smm.length > 1) ? smm : '0' + smm;
        var stime = hh + ':' + smm;

        // add message box to chat box
        var s = voyc.Chat.posttemplate;
        s = s.replace(/%side%/g, side);
        s = s.replace(/%user%/g, name);
        s = s.replace(/%message%/g, message);
        s = s.replace(/%time%/g, stime);

        var m = document.createElement('div');
        m.innerHTML = s;
        this.chatcontent.appendChild(m);

        this.chatscroller.scrollTop = this.chatscroller.scrollHeight;
        document.getElementById('guestpost').focus();

        // add multiple choice options
        var self = this;
        var soptions = '';
        document.getElementById('mchoices').innerHTML = '';
        if (mchoice) {
                for (var i=0; i<mchoice.length; i++) {
                        var opt = document.createElement('button');
                        opt.id = 'opt_' + i;
                        opt.innerHTML = mchoice[i];
                        document.getElementById('mchoices').appendChild(opt);
                        opt.addEventListener('click', function(e) {
                                var s = e.target.innerHTML;
                                self.post(self.idguest,s);
                        }, false);
                }
        }

  //      (new voyc.Observer).publish('chat-posted','chat',{userid:id,msg:message,choice:mchoice});
        return m;
}
voyc.Chat.prototype.init = function(conversation) {
        // draw chat window with all posts
}

voyc.Chat.prototype.save = function(name, conversation) {
        // save conversation to local storage
}

voyc.Chat.prototype.restore = function(name) {
        // restore conversation from local storage
}

/** 
        save conversation on every post? 
*/
voyc.conversation = {
        users: [
                /* {name:'Samantha', host:true, me:false}, */
        ],
        posts: [
                /* {user:1, date:'24Jun2018', message:'hello' }, */
        ]
};
