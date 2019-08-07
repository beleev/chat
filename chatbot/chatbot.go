package chatbot

import (
	"fmt"
	"flag"
	"net"
	"log"

	"google.golang.org/grpc"
	"github.com/tinode/chat/pbx"
	"context"
	"time"
)


func initServer(port string) (*grpc.Server, error) {
	if port == "" {
		return nil, nil
	}
	lis, err := net.Listen("tcp", fmt.Sprint(":%s", port))
	if err != nil {
		log.Fatal("failed to listen: %v", err)
		return nil, err
	}

	srv := grpc.NewServer()
	pluginServer := new(pbx.PluginServer)
	pbx.RegisterPluginServer(srv, pluginServer)

	go func() {
		if err := srv.Serve(lis); err != nil {
			log.Println("gRPC server failed:", err)
		}
	}()

	return srv, nil
}

func initClient(addr string, secret string) () {
	conn, err := grpc.Dial(addr, grpc.WithInsecure())
	if err != nil {
		log.Fatalf("grpc.Dial err: %v", err)
	}
	defer conn.Close()
	client := pbx.NewNodeClient(conn)

	ctx, cancel := context.WithTimeout(context.Background(), 10 * time.Second)
	defer cancel()
	stream, err := client.MessageLoop(ctx)
	if err != nil {
		log.Fatalf("%v.RouteChat(_) = _, %v", client, err)
	}

	waitc := make(chan struct{})
	queue := make(chan *pbx.ClientMsg)


}

func closeBot()  {
	
}

func messageLoop()  {

}

func hello() *pbx.ClientMsg {
	return nil
}

func main() {
	var pin = flag.String("auth", "", "login using basic authentication PIN")
	var quote = flag.String("quotes", "./quotes.txt", "file with messages for the chatbot to use, one message per line")
	flag.Parse()
	
	fmt.Println("Load PIN: " + *pin)
	fmt.Println("Load quote: " + *quote)

	initServer("8086")
	initClient("8088", "test:test")
	defer closeBot();

	for {
		messageLoop()
	}

}