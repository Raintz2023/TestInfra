#include "Ate.h"

int main(int argc, char** argv) {

    for (int y = -10; y <= 10; y++) {
        for (int x = 0; x <= 10; x++) {
            auto wave_name = std::format("/root/Code/TestInfra/C++/wave/wave_{}_{}.vcd", x, y);  

            uint8_t top_data = 0xF0;
            uint64_t addr;

            ATE ate{wave_name, false, top_data};

            ate.mr_write(0, 56);
            ate.mr_write(1, 54);

            for (int j = 0; j < 10; j++) {
                ate.tick();
            }
            
            addr = 0;
            ate.write(addr);

            for (int j = 0; j < 40; j++) {
                ate.tick();
            }

            ate.drive(x, false);
            ate.drive(x, true);
            ate.drive(x, false);
            ate.drive(x, true);

            for (int j = 0; j < 10; j++) {
                ate.tick();
            }

            addr = 0;
            ate.read(addr);

            for (int j = 0; j < 50; j++) {
                ate.tick();
            }

            ate.sample(y, false);
            ate.sample(y, true);
            ate.sample(y, false);
            ate.sample(y, true);

            for (int j = 0; j < 50; j++) {
                ate.tick();
            }

            ate.compare();

            for (int j = 0; j < 10; j++) {
                ate.tick();
            }
        }
        printf("\n");
    }
    printf("\n");


    return 0;
}