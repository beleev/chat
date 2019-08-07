package main


import (
	"C"
	"flag"
	"io/ioutil"
	"time"
	"os"
	"encoding/json"
	"log"
	"math/rand"
	"strings"
	"fmt"

	jcr "github.com/DisposaBoy/JsonConfigReader"
	_ "github.com/tinode/chat/server/db/mysql"
	_ "github.com/tinode/chat/server/db/rethinkdb"
	"github.com/tinode/chat/server/store"
	"github.com/tinode/chat/server/store/types"
	"github.com/tinode/chat/server/auth"
	_ "github.com/tinode/chat/server/auth/basic"
)

type Scene struct {
	Topics       []Topic      `json:"topics"`
	Messages     []Message    `json:"messages"`
}

type Topic struct {
	Name         string       `json:"name"`
	Member       []string     `json:"member"`
}

type Message struct {
	Timeline     string       `json:"time"`
	UserName     string       `json:"from"`
	Topic        string       `json:"to"`
	Note		 string       `json:"message"`
}

type vcard struct {
	Fn    string       `json:"fn" db:"fn"`
	Photo *photoStruct `json:"photo,omitempty" db:"photo"`
}

type photoStruct struct {
	Type string `json:"type" db:"type"`
	Data []byte `json:"data" db:"data"`
}

type configType struct {
	StoreConfig json.RawMessage `json:"store_config"`
}

func injectScene(reset bool, config string, scene *Scene, userName string) string {
	var err error

	defer store.Close()

	err = store.Open(1, config)
	if err != nil {
		if strings.Contains(err.Error(), "Database not initialized") {
			log.Println("Database not found. Creating.", err)
		} else if strings.Contains(err.Error(), "Invalid database version") {
			log.Println("Wrong DB version, dropping and recreating the database.", err)
		} else {
			log.Fatal("Failed to init DB adapter:", err)
		}
	} else {
		log.Println("Start to insert scene to DB.", store.GetAdapterName())
	}

	if reset {
		err = store.InitDb(config, true)
		if err != nil {
			log.Fatal("Failed to init DB:", err)
		}
	}

	topicList := make([]string, 0)
	userList := make(map[string]string)
	// 获取Topic中的所有用户
	for _, topic := range scene.Topics {
		topicList = append(topicList, topic.Name);
		for _, member := range topic.Member {
			if _, ok := userList[member]; !ok {
				userList[member] = ""
			}
		}
	}
	// 获取message中的所有用户
	for _, message := range scene.Messages {
		if _, ok := userList[message.UserName]; !ok {
			userList[message.UserName] = ""
		}
	}

	nameIndex := make(map[string]string, len(userList))

	authIndex := make(map[string]string, len(userList))
	messages := make([]map[string]string, len(scene.Messages))

	script := make(map[string]interface{}, 0)
	script["roles"] = authIndex
	script["messages"] = messages

	fmt.Println("开始生成机器人账户...")
	if len(userList) == 0 {
		log.Fatal("No user provide, exit.")
		return ""
	}
	for user, _ := range userList {
		createUser(user, &nameIndex, &authIndex)
	}

	fmt.Println("开始生成聊天场景...")
	for _, topic := range topicList {
		createTopic(topic, &nameIndex)
	}

	fmt.Println("开始建立场景关系...")
	for _, ss := range scene.Topics {
		want := types.ModeCPublic
		given := types.ModeCPublic
		for _, member := range ss.Member {
			if err = store.Subs.Create(&types.Subscription{
				ObjHeader: types.ObjHeader{CreatedAt: getCreatedTime("0h")},
				User:      nameIndex[member],
				Topic:     nameIndex[ss.Name],
				ModeWant:  want,
				ModeGiven: given,
				Private:   ""}); err != nil {

				log.Fatal(err)
			}
		}
	}

	fmt.Println("开始注入测试账号...")
	createUser(userName, &nameIndex, &authIndex)

	// 和每个topic进行绑定
	for _, ss := range scene.Topics {
		want := types.ModeCPublic
		given := types.ModeCPublic
		if err = store.Subs.Create(&types.Subscription{
			ObjHeader: types.ObjHeader{CreatedAt: getCreatedTime("0h")},
			User:      nameIndex[userName],
			Topic:     nameIndex[ss.Name],
			ModeWant:  want,
			ModeGiven: given,
			Private:   ""}); err != nil {

			log.Fatal(err)
		}
	}

	// 和每个产生对话的机器人进行绑定
	uid := types.ParseUid(nameIndex[userName])

	messageBot := make(map[string]string)
	for _, message := range scene.Messages {
		if _, ok := messageBot[message.UserName]; !ok {
			messageBot[message.UserName] = ""
		}
	}

	for bot, _ := range messageBot {
		peerUid := types.ParseUid(nameIndex[bot])
		topic := uid.P2PName(peerUid)
		created := getCreatedTime("0h")

		// Assign default access mode
		s0want := types.ModeCP2P
		s0given := types.ModeCP2P
		s1want := types.ModeCP2P
		s1given := types.ModeCP2P

		err := store.Topics.CreateP2P(
			&types.Subscription{
				ObjHeader: types.ObjHeader{CreatedAt: created},
				User:      uid.String(),
				Topic:     topic,
				ModeWant:  s0want,
				ModeGiven: s0given,
				Private:   ""},
			&types.Subscription{
				ObjHeader: types.ObjHeader{CreatedAt: created},
				User:      peerUid.String(),
				Topic:     topic,
				ModeWant:  s1want,
				ModeGiven: s1given,
				Private:   ""})

		if err != nil {
			log.Fatal(err)
		}
	}

	// 转化message schema为可执行格式
	for index, message := range scene.Messages {
		tranportedMsg := map[string]string{}
		tranportedMsg["time"] = message.Timeline
		tranportedMsg["from"] = authIndex[message.UserName]
		if "" == message.Topic {
			tranportedMsg["to"] = uid.P2PName(types.ParseUid(nameIndex[message.UserName]))
		} else {
			tranportedMsg["to"] = nameIndex[message.Topic]
		}
		tranportedMsg["text"] = message.Note
		messages[index] = tranportedMsg
	}

	ret, _ :=  json.Marshal(script)
	return string(ret)
}

func getCreatedTime(delta string) time.Time {
	dd, err := time.ParseDuration(delta)
	if err != nil && delta != "" {
		log.Fatal("Invalid duration string", delta)
	}
	return time.Now().UTC().Round(time.Millisecond).Add(dd)
}

func genTopicName() string {
	return "grp" + store.GetUidString()
}

// Generates password of length n
func getPassword(n int) string {
	const letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

	b := make([]byte, n)
	for i := range b {
		b[i] = letters[rand.Intn(len(letters))]
	}
	return string(b)
}

func createUser(user string, nameIndex *map[string]string, authIndex *map[string]string) {
	userInfo := types.User {
		State: 1,
		Access: types.DefaultAccess{
			Auth: types.ModeCP2P,
			Anon: types.ModeNone,
		},
		Public: vcard{Fn: user},
	}

	userInfo.CreatedAt = getCreatedTime("0h")

	userPin := getPassword(8)
	userInfo.Tags = make([]string, 0)
	userInfo.Tags = append(userInfo.Tags, "basic:" + userPin)
	userInfo.Tags = append(userInfo.Tags, "email:" + userPin + "@interv.com")

	// store.Users.Create will subscribe user to !me topic but won't create a !me topic
	if _, err := store.Users.Create(&userInfo, ""); err != nil {
		log.Fatal(err)
	}

	if err := store.Users.SaveCred(&types.Credential{
		User: userInfo.Id,
		Method: "email",
		Value:  userPin + "@interv.com",
		Done:   true,
	}); err != nil {
		log.Fatal(err)
	}

	authLevel := auth.LevelAuth
	authHandler := store.GetAuthHandler("basic")
	authHandler.Init(`{"add_to_tags": true}`, "basic")
	if _, err := authHandler.AddRecord(&auth.Rec{Uid: userInfo.Uid(), AuthLevel: authLevel},
		[]byte(userPin+":"+userPin)); err != nil {
		log.Fatal(err)
	}

	(*nameIndex)[user] = userInfo.Id
	(*authIndex)[user] = userPin
}

func createTopic(topicName string, nameIndex *map[string]string) {
	name := genTopicName()
	(*nameIndex)[topicName] = name

	accessAuth := types.ModeCPublic
	accessAnon := types.ModeCReadOnly
	topic := &types.Topic{
		ObjHeader: types.ObjHeader{Id: name},
		Access: types.DefaultAccess{
			Auth: accessAuth,
			Anon: accessAnon,
		},
		Public: vcard{Fn: topicName},
	}
	var owner types.Uid
	topic.CreatedAt = getCreatedTime("0h")

	if err := store.Topics.Create(topic, owner, ""); err != nil {
		log.Fatal(err)
	}
}

//export initScene
func initScene(userNamePara, schemaPara, dbConfFilePara *C.char) *C.char {
	userName := C.GoString(userNamePara)
	schema := C.GoString(schemaPara)
	dbConfFile := C.GoString(dbConfFilePara)

	var scene Scene

	rand.Seed(time.Now().UnixNano())
	err := json.Unmarshal([]byte(schema), &scene)
	if err != nil {
		log.Fatal(err)
	}

	var config configType
	if file, err := os.Open(dbConfFile); err != nil {
		log.Fatal("Failed to read config file:", err)
	} else if err = json.NewDecoder(jcr.New(file)).Decode(&config); err != nil {
		log.Fatal("Failed to parse config file:", err)
	}

	return C.CString(injectScene(false, string(config.StoreConfig), &scene, userName))
}

func main()  {
	var datafile = flag.String("data", "", "name of file with sample data to load")
	var conffile = flag.String("config", "./tinode.conf", "config of the database connection")
	flag.Parse()

	conf := *conffile
	if *datafile != "" {
		raw, err := ioutil.ReadFile(*datafile)
		if err != nil {
			log.Fatal("Failed to parse data:", err)
		}
		fmt.Println(C.GoString(initScene(C.CString("小虾米"), C.CString(string(raw)), C.CString(conf))))
	}
}
